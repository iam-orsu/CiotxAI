package engine

import (
	"regexp"
	"strings"
)

// Sanitize strips PII, secrets, and identifying information from code
// before it's sent to the LLM. Returns sanitized content.
func Sanitize(content string) string {
	for _, rule := range sanitizeRules {
		content = rule.re.ReplaceAllString(content, rule.replacement)
	}
	return content
}

type sanitizeRule struct {
	re          *regexp.Regexp
	replacement string
}

var sanitizeRules = []sanitizeRule{
	// API keys
	{regexp.MustCompile(`sk-[a-zA-Z0-9]{32,}`), "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`AKIA[0-9A-Z]{16}`), "AKIAXXXXXXXXXXXXXXXX"},
	{regexp.MustCompile(`github_pat_[a-zA-Z0-9_]{22,}`), "github_pat_xxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`), "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`gho_[a-zA-Z0-9]{36}`), "gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`ghu_[a-zA-Z0-9]{36}`), "ghu_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`ghs_[a-zA-Z0-9]{36}`), "ghs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`glpat-[a-zA-Z0-9\-]{20,}`), "glpat-xxxxxxxxxxxxxxxxxxxx"},
	{regexp.MustCompile(`xox[baprs]-[a-zA-Z0-9\-]{10,}`), "xoxx-xxxxxxxxxxxx"},

	// Private keys
	{regexp.MustCompile(`(?s)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----.+?-----END (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----`),
		"-----BEGIN PRIVATE KEY-----\n[REDACTED]\n-----END PRIVATE KEY-----"},

	// Connection strings
	{regexp.MustCompile(`(postgres|mysql|mongodb|redis)://[^@\s]+@[^/\s]+`),
		"$1://user:password@host:port"},

	// Emails
	{regexp.MustCompile(`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`),
		"user@example.com"},

	// IPs
	{regexp.MustCompile(`\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b`), "10.0.0.1"},
	{regexp.MustCompile(`\b(172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b`), "172.16.0.1"},
	{regexp.MustCompile(`\b(192\.168\.\d{1,3}\.\d{1,3})\b`), "192.168.1.1"},
	{regexp.MustCompile(`\b(127\.0\.0\.1)\b`), "127.0.0.1"},

	// JWTs
	{regexp.MustCompile(`eyJ[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,}`),
		"eyJhbGciOi...token...xxxxxxxx"},

	// AWS account IDs
	{regexp.MustCompile(`\b\d{12}\b`), "000000000000"},
}

// RedactSummary describes what was redacted from the code.
func RedactSummary(original, sanitized string) []string {
	var changed []string
	for _, rule := range sanitizeRules {
		matches := rule.re.FindAllString(original, -1)
		for _, m := range matches {
			if !strings.Contains(sanitized, m) {
				short := m
				if len(short) > 40 {
					short = short[:37] + "..."
				}
				changed = append(changed, short)
			}
		}
	}
	return changed
}
