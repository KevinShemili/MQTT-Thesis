package cache

import (
	"benchmark/utility"
	"fmt"
	"os"
	"path/filepath"
)

const fileExtension = ".bin"
const CPABEPublicKeyFileName = "cpabe-public-key"

var cacheDirectory = utility.ParseStringFromEnv("CACHE_DIRECTORY")

// Persist file in cache
func StoreFile(fileName string, fileContent []byte) {

	if err := os.MkdirAll(cacheDirectory, utility.DirectoryPermissions); err != nil {
		panic(err)
	}

	if err := os.WriteFile(getFilePath(fileName), fileContent, utility.FilePermissions); err != nil {
		panic(err)
	}
}

// Load a fixture from the cache, panicking if it was never provisioned
func LoadFile(fileName string) []byte {

	content, err := os.ReadFile(getFilePath(fileName))
	if err != nil {
		panic(fmt.Sprintf("fixture %q was never provisioned", fileName))
	}

	return content
}

func getFilePath(fileName string) string {
	return filepath.Join(cacheDirectory, fileName+fileExtension)
}
