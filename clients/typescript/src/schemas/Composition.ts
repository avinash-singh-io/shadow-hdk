// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Component = string
export type Id = string
export type Name = string
export type Ref = (string | null)
export type Inputs = Binding[]
export type Kind = "invoke"
export type Component1 = string
export type Id1 = string
export type Inputs1 = Binding[]
export type Kind1 = "await"
export type Id2 = string
export type Kind2 = "sequence"
export type Id3 = string
export type Kind3 = "fan_out"
export type JsonValue = unknown
export type Path = string
export type Id4 = string
export type Kind4 = "until"
export type MaxIterations = number
export type Step = (Invoke | Await | Sequence | FanOut | Until)
export type Steps2 = (Invoke | Await | Sequence | FanOut | Until)[]
export type Steps1 = (Invoke | Await | Sequence | FanOut | Until)[]
export type Steps = (Invoke | Await | Sequence | FanOut | Until)[]

/**
 * A first-class value: visible while it runs, changeable mid-flight, emitted as an event.
 */
export interface Composition {
steps?: Steps
}
export interface Invoke {
component: Component
id: Id
inputs?: Inputs
kind?: Kind
}
/**
 * One input: either a literal value or a reference to an earlier step's output by handle.
 */
export interface Binding {
name: Name
ref?: Ref
value?: unknown
}
/**
 * Wait for something slow — a person, a job. Compiles to an interrupt.
 */
export interface Await {
component: Component1
id: Id1
inputs?: Inputs1
kind?: Kind1
}
export interface Sequence {
id: Id2
kind?: Kind2
steps?: Steps1
}
export interface FanOut {
id: Id3
kind?: Kind3
steps?: Steps2
}
/**
 * Loop with a stop: repeat ``step`` until ``condition`` holds, at most ``max_iterations``.
 */
export interface Until {
condition: Condition
id: Id4
kind?: Kind4
max_iterations: MaxIterations
step: Step
}
/**
 * A total, non-looping test over the last observation's output: ``output[path] == equals``.
 */
export interface Condition {
equals: JsonValue
path: Path
}
