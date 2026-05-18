Watch out for a few indicator of incorrect TypeSpec source.

- There should be no new `<ClientMethod>Response` and `<ClientMethod>Headers` model class, where the `<ClientMethod>Headers` model contains `location` variable, or `retry-after` variable.
The generation of these models indicates there is long-running-operation that is not correct specified in TypeSpec as such.
