package cache

import (
	"os"
	"path/filepath"
	"thesis/utility/golang/parser"
	"thesis/utility/golang/permission"
)

func Store(fileName string, fileContent []byte) {

	cacheDirectory := parser.ParseStringFromEnv("CACHE_DIRECTORY")

	if err := os.MkdirAll(cacheDirectory, permission.DirectoryPermissions); err != nil {
		panic(err)
	}

	if err := os.WriteFile(filepath.Join(cacheDirectory, fileName), fileContent, permission.FilePermissions); err != nil {
		panic(err)
	}
}

func Load(fileName string) []byte {

	cacheDirectory := parser.ParseStringFromEnv("CACHE_DIRECTORY")

	content, err := os.ReadFile(filepath.Join(cacheDirectory, fileName))
	if err != nil {
		panic(err)
	}

	return content
}
