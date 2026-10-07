package main

import (
	"fmt"
	"os"
	"thesis/benchmark/cmd/macro/command"
)

func main() {

	if err := command.ExecuteTLSLightPublisher(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=publisher error=%q\n", err)
		os.Exit(1)
	}
}
