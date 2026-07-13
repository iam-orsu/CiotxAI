package engine

import (
	"encoding/json"
	"os/exec"
)

// GitleaksFinding from gitleaks JSON output.
type GitleaksFinding struct {
	Description string `json:"Description"`
	File        string `json:"File"`
	StartLine   int    `json:"StartLine"`
	Secret      string `json:"Secret"`
	Match       string `json:"Match"`
}

// RunGitleaks scans for hardcoded secrets using gitleaks.
// Falls back silently if gitleaks is not installed.
func RunGitleaks(root string) []LLMFinding {
	_, err := exec.LookPath("gitleaks")
	if err != nil {
		return nil // gitleaks not installed, skip
	}

	cmd := exec.Command("gitleaks", "detect", "--source", root, "--no-git", "--report-format=json", "--verbose")
	output, err := cmd.Output()
	if err != nil {
		return nil // gitleaks failed, skip silently
	}

	var gitleaksResults []GitleaksFinding
	if err := json.Unmarshal(output, &gitleaksResults); err != nil {
		return nil
	}

	var findings []LLMFinding
	for _, r := range gitleaksResults {
		secret := r.Secret
		if len(secret) > 50 {
			secret = secret[:47] + "..."
		}
		findings = append(findings, LLMFinding{
			Title:          "Hardcoded secret: " + r.Description,
			Severity:       "critical",
			CWEID:          "CWE-798",
			FilePath:       r.File,
			LineStart:      r.StartLine,
			VulnerableCode: secret,
			Description:    "Hardcoded secret detected: " + r.Description,
			FixSuggestion:  "Remove this secret and use environment variables instead.",
			Confidence:     0.95,
		})
	}
	return findings
}
