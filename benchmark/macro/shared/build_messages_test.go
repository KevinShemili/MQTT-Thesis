package shared

import "testing"

func TestBuildMessagesCreatesRequestedNumberOfMessages(t *testing.T) {

	// Arrange
	messageCount := 3
	payloadSize := 256

	// Act
	messages := BuildMessages(messageCount, payloadSize)

	// Assert
	if len(messages) != messageCount {
		t.Fatalf("expected %d messages, got %d", messageCount, len(messages))
	}
}
