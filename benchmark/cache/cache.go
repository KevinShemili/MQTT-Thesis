package cache

import (
	"os"
	"path/filepath"
	"thesis/benchmark/utility"
)

const fileExtension = ".bin"

var cacheDirectory = utility.ParseStringFromEnv("CACHE_DIRECTORY")

func Store(fileName string, fileContent []byte) {

	if err := os.MkdirAll(cacheDirectory, utility.DirectoryPermissions); err != nil {
		panic(err)
	}

	if err := os.WriteFile(getFilePath(fileName), fileContent, utility.FilePermissions); err != nil {
		panic(err)
	}
}

func Load(fileName string) []byte {

	content, err := os.ReadFile(getFilePath(fileName))
	if err != nil {
		panic(err)
	}

	return content
}

func getFilePath(fileName string) string {
	return filepath.Join(cacheDirectory, fileName+fileExtension)
}
