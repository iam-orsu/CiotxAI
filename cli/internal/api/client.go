package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/ciotx/cli/internal/config"
)

type UserResponse struct {
	ID            string `json:"id"`
	Email         string `json:"email"`
	Name          string `json:"name"`
	Plan          string `json:"plan"`
	PlanStatus    string `json:"plan_status"`
	EmailVerified bool   `json:"email_verified"`
}

func GetMe(cfg *config.Config) (*UserResponse, error) {
	req, err := http.NewRequest("GET", cfg.APIURL+"/v1/auth/me", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+cfg.AccessToken)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch user info: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}

	var user UserResponse
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return nil, fmt.Errorf("failed to parse user response: %w", err)
	}

	return &user, nil
}

func TriggerScan(cfg *config.Config, repoURL string) (map[string]interface{}, error) {
	// First, list projects to find or create one
	projectsBody, err := doRequest(cfg, "GET", cfg.APIURL+"/v1/projects", nil)
	if err != nil {
		return nil, err
	}

	var projList struct {
		Projects []struct {
			ID      string `json:"id"`
			Name    string `json:"name"`
			RepoURL string `json:"repo_url"`
		} `json:"projects"`
		Total int `json:"total"`
	}
	if err := json.Unmarshal(projectsBody, &projList); err != nil {
		return nil, fmt.Errorf("failed to parse projects: %w", err)
	}

	// Find matching project or create one
	projID := ""
	for _, p := range projList.Projects {
		if p.RepoURL == repoURL {
			projID = p.ID
			break
		}
	}

	if projID == "" {
		// Extract name from URL
		name := repoURL
		parts := strings.Split(strings.TrimRight(repoURL, "/"), "/")
		if len(parts) >= 2 {
			name = strings.TrimSuffix(parts[len(parts)-1], ".git")
		}
		createJSON := fmt.Sprintf(`{"name":"%s","repo_url":"%s"}`, name, repoURL)
		createBody, err := doRequest(cfg, "POST", cfg.APIURL+"/v1/projects", strings.NewReader(createJSON))
		if err != nil {
			return nil, fmt.Errorf("failed to create project: %w", err)
		}
		var projResp struct {
			ID string `json:"id"`
		}
		if err := json.Unmarshal(createBody, &projResp); err != nil {
			return nil, fmt.Errorf("failed to parse project: %w", err)
		}
		projID = projResp.ID
	}

	// Trigger scan
	scanBody, err := doRequest(cfg, "POST", cfg.APIURL+"/v1/projects/"+projID+"/scans", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to trigger scan: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(scanBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse scan response: %w", err)
	}

	return result, nil
}

func ListScans(cfg *config.Config) ([]map[string]interface{}, error) {
	// Get projects first, then scans for each
	projectsBody, err := doRequest(cfg, "GET", cfg.APIURL+"/v1/projects", nil)
	if err != nil {
		return nil, err
	}

	var projList struct {
		Projects []struct {
			ID string `json:"id"`
		} `json:"projects"`
	}
	if err := json.Unmarshal(projectsBody, &projList); err != nil {
		return nil, err
	}

	var allScans []map[string]interface{}
	for _, p := range projList.Projects {
		scanBody, err := doRequest(cfg, "GET", cfg.APIURL+"/v1/projects/"+p.ID+"/scans", nil)
		if err != nil {
			continue
		}
		var scanResp struct {
			Scans []map[string]interface{} `json:"scans"`
		}
		if err := json.Unmarshal(scanBody, &scanResp); err != nil {
			continue
		}
		allScans = append(allScans, scanResp.Scans...)
	}

	return allScans, nil
}

func doRequest(cfg *config.Config, method, url string, body io.Reader) ([]byte, error) {
	// Read body BEFORE creating request so both first call and retry get fresh readers
	var bodyBytes []byte
	if body != nil {
		bodyBytes, _ = io.ReadAll(body)
	}

	req, err := http.NewRequest(method, url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+cfg.AccessToken)
	if bodyBytes != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode == 401 {
		// Try refresh
		if err := RefreshToken(cfg); err != nil {
			return nil, fmt.Errorf("authentication expired — please run 'ciotx login'")
		}
		// Retry with new token and fresh body
		retryReq, _ := http.NewRequest(method, url, bytes.NewReader(bodyBytes))
		retryReq.Header.Set("Authorization", "Bearer "+cfg.AccessToken)
		if bodyBytes != nil {
			retryReq.Header.Set("Content-Type", "application/json")
		}
		resp2, err := http.DefaultClient.Do(retryReq)
		if err != nil {
			return nil, err
		}
		defer resp2.Body.Close()
		respBody, _ = io.ReadAll(resp2.Body)
		if resp2.StatusCode >= 400 {
			return nil, fmt.Errorf("API error %d: %s", resp2.StatusCode, string(respBody))
		}
		return respBody, nil
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	return respBody, nil
}

func RefreshToken(cfg *config.Config) error {
	if cfg.RefreshToken == "" {
		return fmt.Errorf("no refresh token available")
	}

	body := fmt.Sprintf(`{"refresh_token":"%s"}`, cfg.RefreshToken)
	resp, err := http.Post(
		cfg.APIURL+"/v1/auth/refresh",
		"application/json",
		strings.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("failed to refresh token: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		cfg.ClearAuth()
		config.Save(cfg)
		return fmt.Errorf("token refresh failed — please log in again")
	}

	var result struct {
		AccessToken  string `json:"access_token"`
		RefreshToken string `json:"refresh_token"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to parse refresh response: %w", err)
	}

	cfg.AccessToken = result.AccessToken
	cfg.RefreshToken = result.RefreshToken
	config.Save(cfg)

	return nil
}
