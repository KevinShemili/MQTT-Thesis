package cache

import (
	"benchmark/utility"
	"fmt"
	"os"
	"path/filepath"
)

const fileExtension = ".bin"
const CPABEPublicKeyFileName = "cpabe-public-key"
const CPABEMasterSecretFileName = "cpabe-master-secret"

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

// Look up a file by its name and return its contents. Important in provisioning process
// - If find returns false -> Create file accordingly
func FindFile(fileName string) ([]byte, bool) {

	content, err := os.ReadFile(getFilePath(fileName))
	if err != nil {
		return nil, false
	}

	return content, true
}

// Same as FindFile but panics if the file is not found
func LoadFile(fileName string) []byte {

	content, found := FindFile(fileName)
	if !found {
		panic(fmt.Sprintf("fixture %q was never provisioned", fileName))
	}

	return content
}

func getFilePath(fileName string) string {
	return filepath.Join(cacheDirectory, fileName+fileExtension)
}
