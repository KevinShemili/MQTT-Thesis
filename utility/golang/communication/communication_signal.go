package communication

import (
	"bufio"
	"fmt"
	"io"
)

func ReadSignal(reader *bufio.Reader, expected string) error {

	signal, err := reader.ReadString('\n')
	if err != nil {
		return err
	}

	if signal != expected+"\n" {
		return fmt.Errorf("expected %s, got %q", expected, signal)
	}

	return nil
}

func WriteSignal(writer io.Writer, signal string) error {

	_, err := fmt.Fprintln(writer, signal)
	return err
}
