package engine

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const systemPrompt = `You are a world-class security researcher performing a code audit.
Read EVERY line of code carefully. Understand how data flows from input to dangerous operations.
Only report a vulnerability if you can PROVE it is exploitable with code evidence.
If you cannot prove exploitability, do NOT report it.
Consider: SQL injection, XSS, command injection, path traversal, SSRF, IDOR, auth bypass, crypto misuse, race conditions, business logic flaws.
For each finding provide: title, severity (critical/high/medium/low), cwe_id, file_path, line_start, line_end, vulnerable_code, description, fix_suggestion, confidence (0-1).

Output ONLY valid JSON: {"findings": [{"title":"...","severity":"...","cwe_id":"...","file_path":"...","line_start":42,"line_end":45,"vulnerable_code":"...","description":"...","fix_suggestion":"...","confidence":0.95}]}
If no vulnerabilities found, return: {"findings": []}`

type LLMFinding struct {
	Title           string  `json:"title"`
	Severity        string  `json:"severity"`
	CWEID           string  `json:"cwe_id"`
	FilePath        string  `json:"file_path"`
	LineStart       int     `json:"line_start"`
	LineEnd         int     `json:"line_end"`
	VulnerableCode  string  `json:"vulnerable_code"`
	Description     string  `json:"description"`
	FixSuggestion   string  `json:"fix_suggestion"`
	Confidence      float64 `json:"confidence"`
}

type LLMResponse struct {
	Findings []LLMFinding `json:"findings"`
}

type LLMClient struct {
	APIKey  string
	BaseURL string
	Model   string
}

func NewLLMClient() (*LLMClient, error) {
	// Try common env vars for API key
	key := firstNonEmpty(
		"CIOTX_API_KEY",
		"DEEPSEEK_API_KEY",
		"ANTHROPIC_API_KEY",
		"OPENAI_API_KEY",
	)
	if key == "" {
		return nil, fmt.Errorf("no LLM API key found. Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY or OPENAI_API_KEY")
	}

	baseURL := firstNonEmpty("CIOTX_RELAY_URL", "DEEPSEEK_BASE_URL")
	if baseURL == "" {
		baseURL = "https://api.deepseek.com/v1"
	}

	model := "deepseek-v4-flash"
	if isSet("ANTHROPIC_API_KEY") && !isSet("DEEPSEEK_API_KEY") {
		model = "claude-sonnet-5-20251001"
		baseURL = "https://api.anthropic.com/v1"
	} else if isSet("OPENAI_API_KEY") && !isSet("DEEPSEEK_API_KEY") && !isSet("ANTHROPIC_API_KEY") {
		model = "gpt-4o"
		baseURL = "https://api.openai.com/v1"
	}

	return &LLMClient{
		APIKey:  key,
		BaseURL: baseURL,
		Model:   model,
	}, nil
}

func (c *LLMClient) ReviewCode(files []DiscoveredFile, projectInfo string) ([]LLMFinding, error) {
	// Build context with files
	var ctx strings.Builder
	ctx.WriteString("PROJECT CONTEXT:\n")
	ctx.WriteString(projectInfo)
	ctx.WriteString("\n\nFILES TO ANALYZE:\n")

	for _, f := range files {
		ctx.WriteString(fmt.Sprintf("\n--- %s ---\n", f.Path))
		lines := strings.Split(f.Content, "\n")
		if len(lines) > 500 {
			lines = lines[:500]
		}
		ctx.WriteString(strings.Join(lines, "\n"))
	}

	sanitizedCode := Sanitize(ctx.String())

	reqBody := map[string]interface{}{
		"model": c.Model,
		"messages": []map[string]string{
			{"role": "system", "content": systemPrompt},
			{"role": "user", "content": sanitizedCode},
		},
		"temperature":      0.1,
		"max_tokens":       4096,
		"response_format":  map[string]string{"type": "json_object"},
	}

	bodyBytes, _ := json.Marshal(reqBody)

	req, err := http.NewRequest("POST", c.BaseURL+"/chat/completions", bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.APIKey)

	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("LLM request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("LLM API error %d: %s", resp.StatusCode, string(respBody)[:500])
	}

	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse LLM response: %w", err)
	}

	if len(result.Choices) == 0 {
		return nil, fmt.Errorf("LLM returned no choices")
	}

	content := result.Choices[0].Message.Content
	// Strip markdown code blocks if present
	content = strings.TrimSpace(content)
	if strings.HasPrefix(content, "```") {
		content = strings.TrimPrefix(content, "```json")
		content = strings.TrimPrefix(content, "```")
		content = strings.TrimSuffix(content, "```")
		content = strings.TrimSpace(content)
	}

	var llmResp LLMResponse
	if err := json.Unmarshal([]byte(content), &llmResp); err != nil {
		return nil, fmt.Errorf("failed to parse LLM findings: %w (raw: %s)", err, content[:min(len(content), 200)])
	}

	return llmResp.Findings, nil
}

func firstNonEmpty(keys ...string) string {
	for _, k := range keys {
		if v := getEnv(k); v != "" {
			return v
		}
	}
	return ""
}

func isSet(key string) bool {
	return getEnv(key) != ""
}

func getEnv(key string) string {
	return os.Getenv(key)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
