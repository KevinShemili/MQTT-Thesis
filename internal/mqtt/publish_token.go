package mqtt

import (
	paho "github.com/eclipse/paho.mqtt.golang"
)

type PublishToken struct {
	token paho.Token
}

var _ IPublishToken = PublishToken{}

func (publishToken PublishToken) Wait() error {
	publishToken.token.Wait()
	return publishToken.token.Error()
}
