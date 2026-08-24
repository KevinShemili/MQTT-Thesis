package support

import "os"

const (
	DirectoryPermissions os.FileMode = 0o700 // Owner can read, write & execute
	FilePermissions      os.FileMode = 0o600 // Owner can read & write
)
