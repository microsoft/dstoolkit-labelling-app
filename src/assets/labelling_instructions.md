# Labelling Guidelines

Please label the generated code using the following scale:

1. **Unusable**
   - **Description**: The generated code brings absolutely no value for the user. It contains significant errors, is not executable, or is completely irrelevant to the prompt.
   - **Example**: 
     ```python
     def add(a, b):
         return a - b
     ```
     **Prompt**: Write a function to add two numbers.
   - **Comments**: The function is supposed to add two numbers but instead subtracts them, making it completely unusable for the given prompt.

2. **Poor**
   - **Description**: The generated code is somewhat helpful but has serious issues. It may require substantial modifications to be useful.
   - **Example**:
     ```python
     def add(a, b):
         print(a + b)
     ```
     **Prompt**: Write a function to add two numbers and return the result.
   - **Comments**: The function performs the addition correctly but prints the result instead of returning it. This would require significant changes to be useful in most contexts.

3. **Average**
   - **Description**: The generated code solves the problem with minor developer modifications, may not be efficient.
   - **Example**:
     ```python
     def add(a, b):
         return a + b

     result = add(2, 3)
     print("The result is " + result)
     ```
     **Prompt**: Write a function to add two numbers and print the result.
   - **Comments**: The function correctly adds two numbers and returns the result, but the print statement will cause a TypeError because it tries to concatenate a string with an integer. Minor modification needed to fix the print statement.

4. **Good**
   - **Description**: The generated code solves the problem, minor improvements possible, somewhat efficient.
   - **Example**:
     ```python
     def add(a, b):
         return a + b

     result = add(2, 3)
     print(f"The result is {result}")
     ```
     **Prompt**: Write a function to add two numbers and print the result.
   - **Comments**: The function correctly adds two numbers and prints the result. The code is functional and efficient, but could be slightly improved by adding type hints or input validation.

5. **Very Good**
   - **Description**: The generated code is efficient, optimized, ready for customer use and follows best practices. It is ready to use without any modifications.
   - **Example**:
     ```python
     def add(a: int, b: int) -> int:
         return a + b

     if __name__ == "__main__":
         result = add(2, 3)
         print(f"The result is {result}")
     ```
     **Prompt**: Write a function to add two numbers and print the result.
   - **Comments**: The function is well-defined with type hints and follows best practices. It includes a main guard to allow the script to be imported without executing the print statement, making it highly reusable and efficient