from bparser import BParser
from intbase import InterpreterBase, ErrorType
import copy

# Integer, Boolean, String, Null, Class, Fields, Methods
class Object:
    def __init__(self, type, value):
        self.type = type
        self.value = value
    
class Integer(Object):
    def __init__(self, value : int):
        super().__init__('int', value)
    
    def to_string(self):
        return str(self.value)
    
class Bool(Object):
    def __init__(self, value : bool):
        super().__init__('bool', value)
    
    def to_string(self):
        return 'true' if self.value else 'false'

class String(Object):
    def __init__(self, value : str):
        super().__init__('str', value)
    
    def to_string(self):
        return str(self.value)

class Null(Object):
    def __init__(self):
        super().__init__('null', None)

    def to_string(self):
        return 'null'

class Method:
    def __init__(self, name, args, statement):
        self.name = name
        self.args = args
        self.statement = statement

class ClassObj(Object):
    def __init__(self, name, body, errorFunc, inputFunc, outputFunc):
        super().__init__('class', body)
        self.name = name
        self.error = errorFunc
        self.get_input = inputFunc
        self.output = outputFunc
    
    def instantiate(self):
        methods = []
        fields = dict()
        for item in self.value:
            if item[0] == 'method':
                for m in methods:
                    if m.name == str(item[1]):
                        self.error(ErrorType.NAME_ERROR, "two methods cannot have the same name")
                methods.append(Method(str(item[1]), item[2], item[3]))
            elif item[0] == 'field':
                for f in fields:
                    if f == item[1]:
                        self.error(ErrorType.NAME_ERROR, "two fields cannot have the same name")
                fields[item[1]] = getData(item[2])
            else:
                self.error(ErrorType.NAME_ERROR, "can only have methods and fields in the next layer from class definition")
        return ClassInstance(self.name, methods, fields, self.error, self.get_input, self.output)

class ClassInstance:
    def __init__(self, name, methods, fields, errorFunc, inputFunc, outputFunc):
        self.name = name
        self.methods = methods
        self.fields = fields

        self.error = errorFunc
        self.get_input = inputFunc
        self.output = outputFunc

    def run_method(self, method_name, passed_in_args=[]):
        method = None
        for methodItem in self.methods:
            if method_name == methodItem.name:
                method = methodItem
        if method is None: self.error(ErrorType.NAME_ERROR, 'method name does not exist')

        statement = method.statement
        
        # shadowing
        paramNameToPassedInArgs = dict(zip(method.args, passed_in_args))
        objectsInScope = dict()
        for field in self.fields:
            objectsInScope[field] = self.fields[field]
        for paramName in paramNameToPassedInArgs:
            if not isinstance(paramNameToPassedInArgs[paramName], ClassInstance):
                obj = copy.deepcopy(paramNameToPassedInArgs[paramName])
            objectsInScope[paramName] = obj

        result = self.run_instruction(statement, objectsInScope)
        return result

    def run_print_instruction(self, statement, objectsInScope):
        console_out = ""
        print_args = statement[1:]
        for arg in print_args:
            if isinstance(arg, list):
                # this can be exp or a call statement
                # TODO do this for now but later add functionality for call and exp
                if str(arg[0]) == 'call':
                    console_out += (self.run_call_instruction(arg, objectsInScope)).to_string()
                else:
                    console_out += (self.evaluateValue(arg, objectsInScope)).to_string()
                # else its an expression
            elif arg[0] == '"':
                # if arg is a string
                console_out += arg[1:-1]
            elif arg == 'true' or arg == 'false':
                # if its the literal true or false
                console_out += str(arg)
            elif arg == 'null':
                console_out += 'null'
            elif str(arg).isnumeric() or (str(arg)[0] == '-' and str(arg)[1:].isnumeric()):
                console_out += str(arg)
            else:
                # this has to be a variable
                if str(arg) in objectsInScope:
                    console_out += (objectsInScope[str(arg)]).to_string()
                else:
                    self.error(ErrorType.NAME_ERROR, 'field or param does not exist')

        self.output(console_out)

    def run_call_instruction(self, statement, objectsInScope):
        objToCall = statement[1]
        funcToCall = statement[2]
        arg_values = statement[3:]
        if objToCall == InterpreterBase.ME_DEF:
            callMethod = None
            for m in self.methods:
                if str(funcToCall) == m.name:
                    callMethod = m
            if callMethod == None: self.error(ErrorType.NAME_ERROR, 'cannot call a method that does not exist')

            # evaluate all argument values
            args_calculated = [self.evaluateValue(rawVal, objectsInScope) for rawVal in arg_values]
            
            result = self.run_method(funcToCall, args_calculated)
            return result

    def run_return_statement(self, statement, objectsInScope):
        if len(statement) > 1:
            objToReturn = self.evaluateValue(statement[1], objectsInScope)
            return objToReturn
        else:
            # this is just a return statement
            return Null()

    def run_if_statement(self, statement, objectsInScope):
        boolExp = statement[1]
        ifBody = statement[2]
        elseBody = statement[3] if len(statement) <= 4 else None
        if boolExp[0] not in {'>', '>=', '<', '<=', '!=', '=='}:
            self.error(ErrorType.TYPE_ERROR, 'if only evaluates bool expressions')
        
        if self.evaluateValue(boolExp, objectsInScope).value:
            return self.run_instruction(ifBody, objectsInScope)
        else:
            if elseBody:
                return self.run_instruction(elseBody, objectsInScope)

    def run_begin_statement(self, statement, objectsInScope):
        for s in statement[1:]:  
            if s[0] == InterpreterBase.RETURN_DEF:
                result = self.run_return_statement(s, objectsInScope)
                return result
            else:
                result = self.run_instruction(s, objectsInScope)

    def run_input_statement(self, statement, objectsInScope):
        def convertToType(data):
            if data == 'true':
                return Bool(True)
            elif data == 'false':
                return Bool(False)
            elif data == 'null':
                return Null()
            elif (data.isnumeric()) or (data[0] == '-' and data[1:].isnumeric()):
                return Integer(int(data))
            else:
                return String(str(data))

        varToReplace = statement[1]
        if varToReplace not in objectsInScope:
            self.error(ErrorType.NAME_ERROR, 'field name does not exist, must input to existing field')
        console_in = self.get_input()
        objectsInScope[varToReplace] = convertToType(console_in)
        return console_in

    def run_set_statement(self, statement, objectsInScope):
        fieldName = statement[1]
        valToSet = self.evaluateValue(statement[2], objectsInScope)
        if fieldName not in objectsInScope:
            self.error(ErrorType.NAME_ERROR, 'field name does not exist, must input to existing field')
        objectsInScope[fieldName] = valToSet
        return valToSet
         

    # print-, call-, return-, if-, begin--, inputi(s)--, set, while
    def run_instruction(self, statement, objectsInScope):
        if statement[0] == InterpreterBase.PRINT_DEF:
            result = self.run_print_instruction(statement, objectsInScope)
        elif statement[0] == InterpreterBase.CALL_DEF:
            result = self.run_call_instruction(statement, objectsInScope)
        elif statement[0] == InterpreterBase.RETURN_DEF:
            result = self.run_return_statement(statement, objectsInScope)
        elif statement[0] == InterpreterBase.IF_DEF:
            result = self.run_if_statement(statement, objectsInScope)
        elif statement[0] == InterpreterBase.BEGIN_DEF:
            result = self.run_begin_statement(statement, objectsInScope)
        elif statement[0] == InterpreterBase.INPUT_INT_DEF or statement[0] == InterpreterBase.INPUT_STRING_DEF:
            result = self.run_input_statement(statement, objectsInScope)
        elif statement[0] == InterpreterBase.SET_DEF:
            result = self.run_set_statement(statement, objectsInScope)
        
        return result

    # evaluates expressions, function calls, and literals
    def evaluateValue(self, data, objectsInScope):
        if isinstance(data, list):
            # this is an expression or a call      
            if data[0] == 'call':
                return self.run_call_instruction(data, objectsInScope)
            else:
                return self.evaluateExpression(data, objectsInScope)
            # else this is an expression
        elif data[0] == '"':
            return String(str(data)[1:-1])
        elif data == 'true':
            return Bool(True)
        elif data == 'false':
            return Bool(False)
        elif data == 'null':
            return Null()
        elif str(data).isnumeric() or (str(data)[0] == '-' and str(data)[1:].isnumeric()):
            return Integer(int(data))
        elif isinstance(data, Integer) or isinstance(data, Bool) or isinstance(data, String) or isinstance(data, Null):
            return data
        else:
            # this has to be a variable
            if str(data) in objectsInScope:
                return objectsInScope[str(data)]
            else:
                self.error(ErrorType.NAME_ERROR, 'field or param does not exist')
        
    
    # comparison operators field, int, bool, string, null -> bool :: > >= < <= != ==
    # arith operators field, int , string (only +) -> bool :: + - * / %
    # bool to bool comparison - bool -> bool :: != == & |
    # unary not operator - !bool_var 

    def evaluateExpression(self, data, objectsInScope):
        operator = data[0]

        if operator in {'>', '>=', '<', '<=', '!=', '=='}:
            # comparison
            result = self.evaluateComparison(data, objectsInScope)
        elif operator in {'+', '-', '*', '/', '%'}:
            # arithmetic op
            result = self.evaluateArithmetic(data, objectsInScope)
        elif operator in {'&', '|', '!'}:
            # bool vs bool
            result = self.evaluateLogical(data, objectsInScope)
        
        return result

    def evaluateComparison(self, data, objectsInScope):
        # {'>', '>=', '<', '<=', '!=', '=='}
        operator = data[0]
        operand1 = self.evaluateValue(data[1], objectsInScope).value
        operand2 = self.evaluateValue(data[2], objectsInScope).value
        
        if type(operand1) == type(None) or type(operand2) == type(None):
            if operator == '==':
                return Bool(operand1 == operand2)
            elif operator == '!=':
                return Bool(operand1 != operand2)
            else:
                self.error(ErrorType.TYPE_ERROR, 'can only use == or != when comparing to null value')

        if type(operand1) != type(operand2):
            return self.error(ErrorType.TYPE_ERROR, 'comparison needs to be done between two same types')

        if operator == '>':
            return Bool(operand1 > operand2)
        elif operator == '>=':
            return Bool(operand1 >= operand2)
        elif operator == '<':
            return Bool(operand1 < operand2)
        elif operator == '<=':
            return Bool(operand1 <= operand2)
        elif operator == '!=':
            return Bool(operand1 != operand2)
        elif operator == '==':
            return Bool(operand1 == operand2)

    def evaluateArithmetic(self, data, objectsInScope):
        # {'+', '-', '*', '/', '%'}
        operator = data[0]
        operand1 = self.evaluateValue(data[1], objectsInScope).value
        operand2 = self.evaluateValue(data[2], objectsInScope).value

        if type(operand1) == str and type(operand2) == str:
            if operator == '+':
                return String(operand1 + operand2)
        elif (type(operand1) == str and type(operand2) != str) or (type(operand1) != str and type(operand2) == str):
            self.error(ErrorType.TYPE_ERROR, 'invalid operations on strings')

        if not(type(operand1) == int and type(operand2) == int):
            self.error(ErrorType.TYPE_ERROR, 'operands for arithmetic operators both need to be integers')
        
        if operator == '+':
            return Integer(operand1 + operand2)
        elif operator == '-':
            return Integer(operand1 - operand2)
        elif operator == '*':
            return Integer(operand1 * operand2)
        elif operator == '/':
            return Integer(operand1 // operand2)
        elif operator == '%':
            return Integer(operand1 % operand2)
        
    def evaluateLogical(self, data, objectsInScope):
        operator = data[0]
        operand1 = self.evaluateValue(data[1], objectsInScope).value
        operand2 = None
        if operator != '!': 
            operand2 = self.evaluateValue(data[2], objectsInScope).value

        if operand2:
            if not(type(operand1) == bool and type(operand2) == bool):
                self.error(ErrorType.TYPE_ERROR, 'logical operators must have both operands be bool')

        if operator == '&':
            return Bool(operand1 and operand2)
        elif operator == '|':
            return Bool(operand1 or operand2)
        elif operator == '!':
            return Bool(not operand1)

def isClassNameValid(class_name: str):
    if not(class_name[0] == '_' or str(class_name[0]).isalpha()):
        return False
    exclude_underscore = class_name.replace('_','')
    return True if exclude_underscore.isalnum() else False

def getData(data):
    if data[0] == '"':
        return String(data[1:-1])
    elif data == 'true':
        return Bool(True)
    elif data == 'false':
        return Bool(False)
    elif data == 'null':
        return Null()
    else:
        return Integer(int(data))
    


class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase’s constructor
        self.classes = dict()
    
    def run(self, program):
        result, parsed_program = BParser.parse(program)
        if result == False:
            return # error
        for cls in parsed_program:
            if cls[1] not in self.classes:
                if isClassNameValid(cls[1]):
                    self.classes[cls[1]] = cls[2:]
                else:
                    self.error(ErrorType.NAME_ERROR, "class name is invalid")
            else:
                self.error(ErrorType.TYPE_ERROR, "two classes with same name cannot exist")
        
        mainClass = None
        if InterpreterBase.MAIN_CLASS_DEF in self.classes:
            mainClass = ClassObj('main', self.classes['main'], self.error, self.get_input, self.output)
        else:
            self.error(ErrorType.NAME_ERROR, "main class is not defined")
        
        classInstance = mainClass.instantiate()
        classInstance.run_method(InterpreterBase.MAIN_FUNC_DEF)
        





program = [
'(class main',
 '(field x 0)',
 '(field y "test")',
 '(method main ()',
  '(begin',
   '(inputi x)',
   '(print x)',
   '(inputs y)',
   '(print y)',
  ')',
 ')',
')',
]

program2 = [
    '(class main',
        '(method fact (n)',
            '(if (== n 1)',
                '(return 1)',
                '(return (* n (call me fact (- n 1))))',
            ')',
        ')',
        '(method main () (print (call me fact 5)))',
    ')'
]

program3 = [
    '(class main',
        '(field b "abc")'
        '(field x null)'
        '(method fact (n)',
            '(return)',
        ')',
        '(method main ()',
            '(begin',
                '(set b (== (call me fact 3) null))',
                '(print b)'
            ')',
        ')',
    ')',
]

program4 = [
    '(class main',
        '(method foo (q)', 
            '(if (== (% q 3) 0)',
                '(return)  # immediately terminates loop and function foo',
                '(set q (- q 1))',
            ')',
        ')',
        '(method main ()',
            '(print (call me foo 6))',
        ')',
    ')',
]

interpreter = Interpreter()
interpreter.run(program4) 


        
