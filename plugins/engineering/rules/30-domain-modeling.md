## Domain modeling

- Objects are always valid. Inside the domain, an object that exists is valid, and code that receives one never checks it again.
- Create domain objects only through a smart constructor: it takes raw input and returns the object or an error. Leave no other way to build one.
- Parse, don't validate. Turn raw input into a domain type once. Never check a value and then pass it on raw.
- An edge is wherever data enters from outside: a controller, a module's facade, deserialization, configuration. Parse only there. Behind it, work with domain types only.
- Input at an edge is primitive and accepts as much as possible, such as a request DTO or the parameters of a facade method. The edge parses it into a valid object, such as a command, before anything else runs.
- No primitive types for domain concepts. An email is an `Email`, never a string. An amount is a `Money`, never an integer or a decimal. An order id is an `OrderId`, never a bare identifier.
- Give a concept its own type when it has rules, a unit or an identity of its own.
