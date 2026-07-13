package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"time"

	"github.com/ciotx/cli/internal/api"
	"github.com/ciotx/cli/internal/auth"
	"github.com/ciotx/cli/internal/config"
)

func Execute() error {
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	// If no arguments, show TUI menu
	if len(os.Args) < 2 {
		return showMenu(cfg)
	}

	// Handle subcommands
	switch os.Args[1] {
	case "login":
		return login(cfg)
	case "scan":
		return scanRepo(cfg)
	case "status":
		return status(cfg)
	case "dashboard":
		return openDashboard(cfg)
	case "--version", "version":
		fmt.Println("ciotx version 0.1.0")
		return nil
	case "--help", "help":
		printHelp()
		return nil
	default:
		return showMenu(cfg)
	}
}

func showMenu(cfg *config.Config) error {
	fmt.Println()
	fmt.Println("  ╔══════════════════════════════════════╗")
	fmt.Println("  ║        🛡️  CIOTX Security            ║")
	fmt.Println("  ║     AI-Powered Code Security         ║")
	fmt.Println("  ╚══════════════════════════════════════╝")
	fmt.Println()

	if cfg.IsAuthenticated() {
		fmt.Println("  Authenticated as:", cfg.UserEmail)
		fmt.Println()
		fmt.Println("  [1] Scan a repository")
		fmt.Println("  [2] View recent scans")
		fmt.Println("  [3] Open web dashboard")
		fmt.Println("  [4] Configure settings")
		fmt.Println()
		fmt.Print("  > ")
	} else {
		fmt.Println("  Welcome! Authenticate to get started.")
		fmt.Println()
		fmt.Println("  [1] Login with browser (recommended)")
		fmt.Println("  [2] Enter API key manually")
		fmt.Println()
		fmt.Print("  > ")

		var choice string
		fmt.Scanln(&choice)

		if choice == "1" {
			return login(cfg)
		}
	}

	return nil
}

func login(cfg *config.Config) error {
	fmt.Println()
	fmt.Println("  Starting authentication...")

	// Step 1: Init PKCE
	result, verifier, err := auth.InitPKCE(cfg.APIURL)
	if err != nil {
		return fmt.Errorf("authentication failed: %w", err)
	}

	// Step 2: Open browser
	verificationURL := fmt.Sprintf("%s/verify?code=%s", cfg.DashboardURL, result.UserCode)
	fmt.Printf("  Opening browser to: %s\n", verificationURL)
	fmt.Println("  Waiting for authentication...")

	if err := openBrowser(verificationURL); err != nil {
		fmt.Printf("  Could not open browser automatically.\n")
		fmt.Printf("  Please open this URL manually:\n")
		fmt.Printf("  %s\n", verificationURL)
	}

	// Step 3: Poll for token
	token, err := auth.PollForToken(cfg.APIURL, result.DeviceCode, verifier, 10*time.Minute)
	if err != nil {
		return fmt.Errorf("authentication failed: %w", err)
	}

	// Step 4: Save tokens
	cfg.AccessToken = token.AccessToken
	cfg.RefreshToken = token.RefreshToken
	config.Save(cfg)

	// Step 5: Fetch user info
	user, err := api.GetMe(cfg)
	if err != nil {
		return fmt.Errorf("authentication succeeded but failed to fetch user info: %w", err)
	}

	cfg.UserID = user.ID
	cfg.UserEmail = user.Email
	config.Save(cfg)

	fmt.Printf("\n  ✅ Authenticated as %s\n", user.Email)
	fmt.Printf("  Plan: %s (%s)\n", user.Plan, user.PlanStatus)
	fmt.Println()

	return nil
}

func scanRepo(cfg *config.Config) error {
	if !cfg.IsAuthenticated() {
		fmt.Println("  Not authenticated. Run 'ciotx login' first.")
		return nil
	}

	// Get repo URL from args
	repoURL := ""
	if len(os.Args) > 2 {
		repoURL = os.Args[2]
	}

	if repoURL == "" {
		fmt.Print("  Repository URL: ")
		fmt.Scanln(&repoURL)
	}

	if repoURL == "" {
		fmt.Println("  No repository URL provided.")
		return nil
	}

	// Call API to find or create project and trigger scan
	resp, err := api.TriggerScan(cfg, repoURL)
	if err != nil {
		return fmt.Errorf("scan failed: %w", err)
	}

	fmt.Println()
	fmt.Printf("  ✅ Scan queued — ID: %s\n", resp["scan_id"])
	fmt.Printf("  📊 Dashboard: %s/dashboard\n", cfg.DashboardURL)
	fmt.Println()
	return nil
}

func status(cfg *config.Config) error {
	if !cfg.IsAuthenticated() {
		fmt.Println("  Not authenticated. Run 'ciotx login' first.")
		return nil
	}

	scans, err := api.ListScans(cfg)
	if err != nil {
		fmt.Printf("  Failed to fetch scans: %v\n", err)
		return nil
	}

	fmt.Println()
	fmt.Printf("  Authenticated as: %s\n", cfg.UserEmail)
	fmt.Println()

	if len(scans) == 0 {
		fmt.Println("  No scans yet. Run 'ciotx scan <repo-url>' to start.")
		fmt.Println()
		return nil
	}

	for _, s := range scans[:min(5, len(scans))] {
		status := s["status"].(string)
		icon := "🟢"
		if status != "completed" {
			icon = "🔄"
		}
		fmt.Printf("  %s Scan %s — %s (%v findings)\n",
			icon, s["id"].(string)[:8], status, s["total_findings"])
	}
	fmt.Println()
	return nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func openDashboard(cfg *config.Config) error {
	dashboardURL := fmt.Sprintf("%s/dashboard", cfg.DashboardURL)
	fmt.Println("  Opening dashboard:", dashboardURL)
	return openBrowser(dashboardURL)
}

func printHelp() {
	fmt.Println()
	fmt.Println("  ciotx                    Interactive TUI menu")
	fmt.Println("  ciotx login              Authenticate with CIOTX")
	fmt.Println("  ciotx status             Show authentication and scan status")
	fmt.Println("  ciotx dashboard          Open web dashboard")
	fmt.Println("  ciotx scan <repo-url>    Trigger a cloud scan")
	fmt.Println("  ciotx scan --path ./     Scan a local directory")
	fmt.Println("  ciotx --version          Show version")
	fmt.Println("  ciotx --help             Show this help")
	fmt.Println()
}

func openBrowser(url string) error {
	switch runtime.GOOS {
	case "linux":
		return exec.Command("xdg-open", url).Start()
	case "darwin":
		return exec.Command("open", url).Start()
	case "windows":
		return exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	default:
		return fmt.Errorf("unsupported platform")
	}
}
