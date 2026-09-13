# `shadow_hdk.adapters.basic`

The adapters small enough that every deployment has them, and real enough that they are not doubles:

| | port | notes |
|---|---|---|
| `AllowAll` | governance | permits everything, including `ASSUME_WORST`. A starting point, never a policy |
| `StdoutSink` | sink | one JSON line per proposal |
| `StdoutObserver`, `CallbackObserver` | observer | one JSON line per event; or a function of your own |
| `SystemClock` | clock | real time, random ids |
| `CallableComponents`, `callable_component` | component | **a Python function becomes a component** — how a host registers its own operations |

`CallableComponents` is the one that matters: it is how a product's own operations — Intent Studio's
25 record verbs, your store's read and write — arrive as components with declared effects. See
`specs/architecture/adapters.md`, *Plugging your record in*.
