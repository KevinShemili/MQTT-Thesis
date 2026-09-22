package shared

import "thesis/internal/message"

func BuildMessages(messageCount int, payloadSize int) []message.Message {

	messages := make([]message.Message, messageCount)

	for messageIndex := range messageCount {
		messages[messageIndex] = message.NewMessage(payloadSize)
	}

	return messages
}
