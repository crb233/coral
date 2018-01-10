
# The Coral Interpreter
### Written by Curtis Bechtel
### Inspired by the Anemone language

Coral is a functional language based on pattern-matching and term-rewriting. In
appearance, Coral is similar to languages like Lisp, Scheme, and Clojure, but
it functions very differently. Rather than applying functions to literals, it
takes a group of atoms (literals) and reduces it according to a user-defined set
of rules.

All statements in Coral are written in the following form:
`<pattern> = <result>`

This statement can be read as "\<pattern> yields \<result>". It represents a
single reduction rule that the interpreter can apply to a term. Rules can only
be loaded into the interpreter from files (libraries).

The only datatype in Coral is the atom. Integers, floats, lists, and other
high-order data types must be simulated by groups of atoms and rules.

For example, the file math.coral might contain:

```
zero = 0
one = s 0
two = s (s 0)
three = s (s (s 0))

+ A 0 = A
+ A (s B) = + (s A) B

* A 0 = 0
* A (s B) = + A (* A B)
```
    
We can then load this file into the interpreter and give it terms to reduce:

```
> * two three
(s (s (s (s (s (s 0))))))
> + three one
(s (s (s (s 0))))
> * two zero
0
```
