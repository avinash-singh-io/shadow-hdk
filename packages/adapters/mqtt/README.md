# shadow-hdk-adapters-mqtt

The first protocol adapter over the device contract (Epic 0007): a subscribed topic is a sensor, a
command topic is an actuator, an event topic is a witness. Speaks MQTT through `paho-mqtt`; the
suite proves it against a broker on localhost that it starts and stops.
