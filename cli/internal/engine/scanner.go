package engine

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// ScanResult holds the complete result of a local scan.
type ScanResult struct {
	ProjectPath    string
	FilesScanned   int
	Languages      string
	Findings       []LLMFinding
	Duration       time.Duration
	SandboxCleaned bool
}

// RunLocalScan executes the full local scan pipeline on a directory.
// Code never leaves the machine. Only findings are returned.
func RunLocalScan(projectPath string) (*ScanResult, error) {
	start := time.Now()

	// Validate path
	absPath, err := filepath.Abs(projectPath)
	if err != nil {
		return nil, fmt.Errorf("invalid path: %w", err)
	}

	info, err := os.Stat(absPath)
	if err != nil || !info.IsDir() {
		return nil, fmt.Errorf("path is not a directory: %s", absPath)
	}

	// Phase 1: Create sandbox + discover files
	fmt.Println("  Phase 1: Creating sandbox...")
	sandbox, cleanup, err := CreateSandbox(absPath)
	if err != nil {
		return nil, fmt.Errorf("sandbox creation failed: %w", err)
	}
	defer func() {
		cleanup()
		fmt.Println("  Sandbox cleaned up.")
	}()

	files, err := DiscoverFiles(absPath)
	if err != nil {
		return nil, fmt.Errorf("file discovery failed: %w", err)
	}

	if len(files) == 0 {
		return &ScanResult{
			ProjectPath:    absPath,
			FilesScanned:   0,
			Duration:       time.Since(start),
			SandboxCleaned: true,
		}, nil
	}

	languages := DetectLanguages(files)
	fmt.Printf("  Phase 1: %d files found (%s)\n", len(files), languages)

	// Phase 2: LLM AI-First Review
	fmt.Println("  Phase 2: AI code review...")
	var aiFindings []LLMFinding

	client, err := NewLLMClient()
	if err != nil {
		fmt.Printf("  ⚠️  LLM not configured: %v\n", err)
		fmt.Println("  Skipping AI review. Running safety net only.")
	} else {
		projectInfo := fmt.Sprintf("Languages: %s\nFiles: %d\nRoot: %s", languages, len(files), absPath)
		aiFindings, err = client.ReviewCode(files, projectInfo)
		if err != nil {
			fmt.Printf("  ⚠️  AI review failed: %v\n", err)
		} else {
			fmt.Printf("  Phase 2: %d findings from AI review\n", len(aiFindings))
		}
	}

	// Phase 3: Safety net (Gitleaks)
	fmt.Println("  Phase 3: Safety net scan...")
	gitleaksFindings := RunGitleaks(sandbox)
	fmt.Printf("  Phase 3: %d findings from Gitleaks\n", len(gitleaksFindings))

	// Merge and deduplicate
	var allFindings []LLMFinding
	allFindings = append(allFindings, aiFindings...)
	seen := map[string]bool{}
	for _, f := range aiFindings {
		key := fmt.Sprintf("%s:%d", f.FilePath, f.LineStart)
		seen[key] = true
	}
	for _, f := range gitleaksFindings {
		key := fmt.Sprintf("%s:%d", f.FilePath, f.LineStart)
		if !seen[key] {
			allFindings = append(allFindings, f)
			seen[key] = true
		}
	}

	duration := time.Since(start)
	fmt.Printf("  Phase 4: Complete — %d findings in %.1fs\n", len(allFindings), duration.Seconds())

	return &ScanResult{
		ProjectPath:    absPath,
		FilesScanned:   len(files),
		Languages:      languages,
		Findings:       allFindings,
		Duration:       duration,
		SandboxCleaned: true,
	}, nil
}

// PushFindings sends scan results to the CIOTX cloud API.
func PushFindings(apiURL, token, projectName string, result *ScanResult) (string, error) {
	// Build findings payload
	type FindingPayload struct {
		Title          string  `json:"title"`
		Severity       string  `json:"severity"`
		CWEID          string  `json:"cwe_id"`
		FilePath       string  `json:"file_path"`
		LineStart      int     `json:"line_start"`
		LineEnd        int     `json:"line_end"`
		VulnerableCode string  `json:"vulnerable_code"`
		Description    string  `json:"description"`
		FixSuggestion  string  `json:"fix_suggestion"`
		Confidence     float64 `json:"confidence"`
	}

	var payload []FindingPayload
	for _, f := range result.Findings {
		payload = append(payload, FindingPayload{
			Title:          f.Title,
			Severity:       f.Severity,
			CWEID:          f.CWEID,
			FilePath:       f.FilePath,
			LineStart:      f.LineStart,
			LineEnd:        f.LineEnd,
			VulnerableCode: f.VulnerableCode,
			Description:    f.Description,
			FixSuggestion:  f.FixSuggestion,
			Confidence:     f.Confidence,
		})
	}

	body, _ := json.Marshal(map[string]interface{}{
		"name":          projectName,
		"findings":      payload,
		"files_scanned": result.FilesScanned,
		"languages":     result.Languages,
		"duration_ms":   result.Duration.Milliseconds(),
	})

	req, _ := http.NewRequest("POST", apiURL+"/v1/scans/local", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to push findings: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	var apiResp struct {
		ScanID  string `json:"scan_id"`
		Message string `json:"message"`
	}
	json.Unmarshal(respBody, &apiResp)

	return apiResp.ScanID, nil
}
