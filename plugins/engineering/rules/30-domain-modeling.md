## Domain modeling

- Objects are always valid. Inside the domain, an object that exists is valid, and code that receives one never checks it again.
- Create domain objects only through a smart constructor: it takes raw input and returns the object or an error. Leave no other way to build one.
- Parse, don't validate. Turn raw input into a domain type once. Never check a value and then pass it on raw.
- Parsing normalizes, such as trimming and casing, so two spellings of one value become equal.
- An edge is wherever data enters from outside: a controller, a module's facade, deserialization, configuration. Parse only there. Behind it, work with domain types only.
- Input at an edge is primitive and accepts as much as possible, such as a request DTO or the parameters of a facade method. The edge parses it into a valid object, such as a command, before anything else runs.
- No primitive types for domain concepts. An email is an `Email`, never a string. An amount is a `Money`, never an integer or a decimal. An order id is an `OrderId`, never a bare identifier.
- Behind the edge, signatures take domain types: `FindUser(UserName)`, never `FindUser(string)`.
- A concept earns its own type when the extreme values of its primitive would be invalid, such as a whole book as a user name or the lowest integer as a quantity.
- Value types compare by value.
- Name types in the domain's own words, never in those of a framework or a third-party API.
