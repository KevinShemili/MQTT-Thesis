package main

import (
	"fmt"
	"os"
	"thesis/benchmark/cmd/macro/command"
)

func main() {

	if err := command.ExecutePSKSubscriber(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR role=subscriber error=%q\n", err)
		os.Exit(1)
	}
}
