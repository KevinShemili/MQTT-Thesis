package cache

import (
	"os"
	"path/filepath"
	"thesis/benchmark/utility"
)

var cacheDirectory = utility.ParseStringFromEnv("CACHE_DIRECTORY")

func Store(fileName string, fileContent []byte) {

	if err := os.MkdirAll(cacheDirectory, utility.DirectoryPermissions); err != nil {
		panic(err)
	}

	if err := os.WriteFile(filepath.Join(cacheDirectory, fileName), fileContent, utility.FilePermissions); err != nil {
		panic(err)
	}
}

func Load(fileName string) []byte {

	content, err := os.ReadFile(filepath.Join(cacheDirectory, fileName))
	if err != nil {
		panic(err)
	}

	return content
}
