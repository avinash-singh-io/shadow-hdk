# shadow-hdk-adapters-devices

One device contract with three roles (D31): a `Sensor` reads the world (`reads: {world}`), an
`Actuator` writes it irreversibly and leaves an `Acted` receipt under a lease read at the moment of
the act, a `Witness` reports acts that happened without us as observed receipts. `DeviceComponents`
turns a set of devices into a component port; the fakes in `testing` are the first devices, and the
protocol adapters (MQTT first) are written over this contract.
