package engine

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

var skipDirs = map[string]bool{
	"node_modules": true, ".git": true, "__pycache__": true, "venv": true,
	".venv": true, "env": true, ".next": true, "dist": true, "build": true,
	"target": true, ".tox": true, ".mypy_cache": true, ".pytest_cache": true,
	".ruff_cache": true, "vendor": true, "bower_components": true,
}

var skipExtensions = map[string]bool{
	".pyc": true, ".pyo": true, ".so": true, ".dylib": true, ".dll": true,
	".exe": true, ".bin": true, ".jpg": true, ".jpeg": true, ".png": true,
	".gif": true, ".svg": true, ".ico": true, ".woff": true, ".woff2": true,
	".ttf": true, ".eot": true, ".mp4": true, ".mp3": true, ".zip": true,
	".tar": true, ".gz": true, ".lock": true, ".log": true,
}

var sourceExtensions = map[string]bool{
	".py": true, ".js": true, ".ts": true, ".tsx": true, ".jsx": true,
	".go": true, ".java": true, ".rb": true, ".php": true, ".rs": true,
	".swift": true, ".kt": true, ".c": true, ".h": true, ".cpp": true,
	".hpp": true, ".cs": true, ".vue": true, ".svelte": true, ".sql": true,
	".yaml": true, ".yml": true, ".toml": true, ".tf": true,
}

// DiscoveredFile represents a source file found during scanning.
type DiscoveredFile struct {
	Path    string
	Content string
	Size    int64
}

// DiscoverFiles walks a directory and returns all source files.
// Skips build artifacts, binaries, node_modules, etc.
func DiscoverFiles(root string) ([]DiscoveredFile, error) {
	var files []DiscoveredFile

	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // skip files we can't read
		}

		if info.IsDir() {
			if skipDirs[info.Name()] {
				return filepath.SkipDir
			}
			return nil
		}

		if !info.Mode().IsRegular() {
			return nil
		}

		ext := strings.ToLower(filepath.Ext(path))
		if skipExtensions[ext] {
			return nil
		}

		if !sourceExtensions[ext] && !isSpecialFile(info.Name()) {
			return nil
		}

		if info.Size() > 10*1024*1024 { // 10MB max per file
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			return nil
		}

		relPath, _ := filepath.Rel(root, path)
		files = append(files, DiscoveredFile{
			Path:    relPath,
			Content: string(content),
			Size:    info.Size(),
		})

		return nil
	})

	return files, err
}

func isSpecialFile(name string) bool {
	lower := strings.ToLower(name)
	return lower == "dockerfile" || lower == "makefile" || lower == "docker-compose.yml"
}

// CreateSandbox creates a hardlinked copy of source files in a temp directory.
// Returns the sandbox path and a cleanup function.
func CreateSandbox(root string) (string, func(), error) {
	sandbox, err := os.MkdirTemp("", "ciotx-scan-")
	if err != nil {
		return "", nil, fmt.Errorf("failed to create sandbox: %w", err)
	}

	cleanup := func() {
		os.RemoveAll(sandbox)
	}

	// Copy only source files into sandbox
	files, err := DiscoverFiles(root)
	if err != nil {
		cleanup()
		return "", nil, fmt.Errorf("failed to discover files: %w", err)
	}

	for _, f := range files {
		dest := filepath.Join(sandbox, f.Path)
		if err := os.MkdirAll(filepath.Dir(dest), 0755); err != nil {
			cleanup()
			return "", nil, fmt.Errorf("failed to create sandbox directory: %w", err)
		}
		if err := os.WriteFile(dest, []byte(f.Content), 0444); err != nil { // read-only
			cleanup()
			return "", nil, fmt.Errorf("failed to copy file to sandbox: %w", err)
		}
	}

	return sandbox, cleanup, nil
}

// DetectLanguages returns a human-readable language summary.
func DetectLanguages(files []DiscoveredFile) string {
	extCount := map[string]int{}
	for _, f := range files {
		ext := strings.ToLower(filepath.Ext(f.Path))
		if ext != "" {
			extCount[ext]++
		}
	}

	langMap := map[string]string{
		".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
		".tsx": "React/TS", ".jsx": "React/JS", ".go": "Go",
		".java": "Java", ".rb": "Ruby", ".php": "PHP", ".rs": "Rust",
		".swift": "Swift", ".kt": "Kotlin", ".vue": "Vue", ".svelte": "Svelte",
	}

	var detected []string
	for ext, name := range langMap {
		if extCount[ext] > 0 {
			detected = append(detected, name)
		}
	}

	if len(detected) == 0 {
		return "unknown"
	}
	return strings.Join(detected, ", ")
}
