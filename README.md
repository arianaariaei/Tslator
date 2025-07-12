# Teslator: A Compiler for TesLang

**Teslator** is a compiler for the **TesLang** programming language, developed as part of the *Compiler Design* course at Babol Noshirvani University of Technology. TesLang is a simple C-like educational language featuring basic types, user-defined functions, arrays, conditionals, loops, and string handling.


**Instructor and Developer:** Dr. Gholami

---

## Language Features

TesLang supports the following data types:

- `int`: Integer values  
- `vector`: Arrays of integers  
- `str`: String literals  
- `mstr`: Multi-line strings  
- `bool`: Boolean values (`true`, `false`)

---

## Project Structure

| File/Folder         | Description                                      |
|---------------------|--------------------------------------------------|
| `lexer.py`          | Lexical analyzer built with PLY                  |
| `parser.py`         | Parser using TesLang grammar rules               |
| `AST.py`            | Abstract Syntax Tree node classes                |
| `SymbolTable.py`    | Symbol management, scoping, and type checking    |
| `IRGenerator.py`    | Intermediate Representation (IR) code generation |
| `main.py`           | Entry point of the compiler                      |

---

## Project Phases

This compiler was developed in three main phases:

### Phase 1 – Lexical Analysis
- Token recognition for all TesLang keywords and operators  
- Support for nested comments (`</ ... />`)  
- Error reporting for malformed tokens  

### Phase 2 – Parsing and Semantic Analysis
- PLY-based parser using a hand-written BNF grammar  
- Construction of the Abstract Syntax Tree (AST)  
- Symbol table construction with scoped entries  
- Type checking and semantic validation (e.g., return consistency, redefinition, undeclared use)  

### Phase 3 – IR Code Generation
- Emits low-level IR resembling assembly  
- Register allocation for variables and temporaries  
- Correct return handling and expression evaluation  

---

## Author

- [@arianaariaei](https://github.com/arianaariaei)  

---

## 📄 License

*MIT License*

---
