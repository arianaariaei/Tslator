import sys
from lexer import tokenize
from tabulate import tabulate


def process_input(filename):
    with open(filename, 'r') as file:
        return file.read()


def print_tokens(tokens_list):
    table_data = []
    for token in tokens_list:
        table_data.append([token.lineno, token.lexpos, token.type, token.value])

    headers = ["Line", "Position", "Token", "Value"]
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))


def main():
    input_text = process_input("input/sample_code.tes")

    tokens_list = tokenize(input_text)

    print_tokens(tokens_list)


if __name__ == "__main__":
    main()
