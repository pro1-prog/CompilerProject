#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <cctype>
#include <sstream>
using namespace std;

enum TokenType {
    T_INT, T_FLOAT, T_BOOL, T_IF, T_ELSE, T_WHILE,
    T_TRUE, T_FALSE, T_IDENTIFIER, T_NUMBER, T_SEMICOLON,
    T_ASSIGN, T_PLUS, T_MINUS, T_MUL, T_DIV,
    T_LT, T_GT, T_LE, T_GE, T_EQ, T_NE,
    T_LPAREN, T_RPAREN, T_LBRACE, T_RBRACE, T_END, T_INVALID
};

struct Token {
    TokenType type;
    string lexeme;
    int line;
};

string tokenName(TokenType t) {
    switch(t) {
        case T_INT: return "INT";
        case T_FLOAT: return "FLOAT";
        case T_BOOL: return "BOOL";
        case T_IF: return "IF";
        case T_ELSE: return "ELSE";
        case T_WHILE: return "WHILE";
        case T_TRUE: return "TRUE";
        case T_FALSE: return "FALSE";
        case T_IDENTIFIER: return "IDENTIFIER";
        case T_NUMBER: return "NUMBER";
        case T_SEMICOLON: return "SEMICOLON";
        case T_ASSIGN: return "ASSIGN";
        case T_PLUS: return "PLUS";
        case T_MINUS: return "MINUS";
        case T_MUL: return "MUL";
        case T_DIV: return "DIV";
        case T_LT: return "LT";
        case T_GT: return "GT";
        case T_LE: return "LE";
        case T_GE: return "GE";
        case T_EQ: return "EQ";
        case T_NE: return "NE";
        case T_LPAREN: return "LPAREN";
        case T_RPAREN: return "RPAREN";
        case T_LBRACE: return "LBRACE";
        case T_RBRACE: return "RBRACE";
        case T_END: return "END";
        default: return "INVALID";
    }
}

class Lexer {
    string src;
    size_t pos = 0;
    int line = 1;

public:
    explicit Lexer(const string& s) : src(s) {}

    vector<Token> tokenize() {
        vector<Token> out;
        while(pos < src.size()) {
            char c = src[pos];

            if(c == '\n') { line++; pos++; continue; }
            if(isspace(static_cast<unsigned char>(c))) { pos++; continue; }

            if(isalpha(static_cast<unsigned char>(c)) || c == '_') {
                size_t start = pos++;
                while(pos < src.size() &&
                      (isalnum(static_cast<unsigned char>(src[pos])) || src[pos] == '_'))
                    pos++;
                string w = src.substr(start, pos-start);
                TokenType t = T_IDENTIFIER;
                if(w=="int") t=T_INT;
                else if(w=="float") t=T_FLOAT;
                else if(w=="bool") t=T_BOOL;
                else if(w=="if") t=T_IF;
                else if(w=="else") t=T_ELSE;
                else if(w=="while") t=T_WHILE;
                else if(w=="true") t=T_TRUE;
                else if(w=="false") t=T_FALSE;
                out.push_back({t,w,line});
                continue;
            }

            if(isdigit(static_cast<unsigned char>(c))) {
                size_t start = pos++;
                bool dot = false;
                while(pos < src.size() && (isdigit(static_cast<unsigned char>(src[pos])) || src[pos]=='.')) {
                    if(src[pos]=='.') {
                        if(dot) break;
                        dot=true;
                    }
                    pos++;
                }
                out.push_back({T_NUMBER,src.substr(start,pos-start),line});
                continue;
            }

            auto add=[&](TokenType t, const string& s) {
                out.push_back({t,s,line});
                pos += s.size();
            };

            if(pos+1 < src.size()) {
                string two = src.substr(pos,2);
                if(two=="<=") { add(T_LE,two); continue; }
                if(two==">=") { add(T_GE,two); continue; }
                if(two=="==") { add(T_EQ,two); continue; }
                if(two=="!=") { add(T_NE,two); continue; }
            }

            switch(c) {
                case ';': add(T_SEMICOLON,";"); break;
                case '=': add(T_ASSIGN,"="); break;
                case '+': add(T_PLUS,"+"); break;
                case '-': add(T_MINUS,"-"); break;
                case '*': add(T_MUL,"*"); break;
                case '/': add(T_DIV,"/"); break;
                case '<': add(T_LT,"<"); break;
                case '>': add(T_GT,">"); break;
                case '(': add(T_LPAREN,"("); break;
                case ')': add(T_RPAREN,")"); break;
                case '{': add(T_LBRACE,"{"); break;
                case '}': add(T_RBRACE,"}"); break;
                default:
                    out.push_back({T_INVALID,string(1,c),line});
                    pos++;
            }
        }
        out.push_back({T_END,"EOF",line});
        return out;
    }
};

enum ValueType { TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_ERROR };

string typeName(ValueType t) {
    if(t==TYPE_INT) return "int";
    if(t==TYPE_FLOAT) return "float";
    if(t==TYPE_BOOL) return "bool";
    return "error";
}

struct Symbol {
    string name;
    ValueType type;
    int line;
};

class Parser {
    vector<Token> tokens;
    size_t cur=0;
    bool syntaxOK=true;
    vector<string> errors;
    unordered_map<string,Symbol> table;

    Token peek() { return tokens[cur]; }
    Token previous() { return tokens[cur-1]; }

    bool check(TokenType t) { return peek().type==t; }

    bool match(TokenType t) {
        if(check(t)) { cur++; return true; }
        return false;
    }

    void syntaxError(const string& msg) {
        syntaxOK=false;
        errors.push_back("Syntax error at line " + to_string(peek().line) + ": " + msg);
    }

    void semanticError(const string& msg, int line) {
        errors.push_back("Semantic error at line " + to_string(line) + ": " + msg);
    }

    void synchronize() {
        while(!check(T_END)) {
            if(previous().type==T_SEMICOLON) return;
            if(check(T_INT)||check(T_FLOAT)||check(T_BOOL)||check(T_IF)||check(T_WHILE))
                return;
            cur++;
        }
    }

    ValueType parseExpression() { return parseEquality(); }

    ValueType parseEquality() {
        ValueType left=parseRelational();
        while(check(T_EQ)||check(T_NE)) {
            cur++;
            ValueType right=parseRelational();
            if(left!=TYPE_ERROR && right!=TYPE_ERROR &&
               left!=right)
                semanticError("comparison operands have different types", previous().line);
            left=TYPE_BOOL;
        }
        return left;
    }

    ValueType parseRelational() {
        ValueType left=parseTerm();
        while(check(T_LT)||check(T_GT)||check(T_LE)||check(T_GE)) {
            cur++;
            ValueType right=parseTerm();
            if(left!=TYPE_ERROR && right!=TYPE_ERROR &&
               !((left==TYPE_INT||left==TYPE_FLOAT) &&
                 (right==TYPE_INT||right==TYPE_FLOAT)))
                semanticError("relational operator requires numeric operands", previous().line);
            left=TYPE_BOOL;
        }
        return left;
    }

    ValueType parseTerm() {
        ValueType left=parseFactor();
        while(check(T_PLUS)||check(T_MINUS)) {
            cur++;
            ValueType right=parseFactor();
            if(left==TYPE_ERROR || right==TYPE_ERROR) left=TYPE_ERROR;
            else if((left==TYPE_BOOL)||(right==TYPE_BOOL)) {
                semanticError("arithmetic operator requires numeric operands", previous().line);
                left=TYPE_ERROR;
            } else if(left==TYPE_FLOAT || right==TYPE_FLOAT) left=TYPE_FLOAT;
            else left=TYPE_INT;
        }
        return left;
    }

    ValueType parseFactor() {
        ValueType left=parseUnary();
        while(check(T_MUL)||check(T_DIV)) {
            cur++;
            ValueType right=parseUnary();
            if(left==TYPE_ERROR || right==TYPE_ERROR) left=TYPE_ERROR;
            else if((left==TYPE_BOOL)||(right==TYPE_BOOL)) {
                semanticError("arithmetic operator requires numeric operands", previous().line);
                left=TYPE_ERROR;
            } else if(left==TYPE_FLOAT || right==TYPE_FLOAT) left=TYPE_FLOAT;
            else left=TYPE_INT;
        }
        return left;
    }

    ValueType parseUnary() {
        if(match(T_MINUS)) {
            ValueType t=parseUnary();
            if(t==TYPE_BOOL)
                semanticError("unary minus cannot be applied to bool", previous().line);
            return t;
        }
        return parsePrimary();
    }

    ValueType parsePrimary() {
        if(match(T_NUMBER)) {
            return previous().lexeme.find('.') != string::npos ? TYPE_FLOAT : TYPE_INT;
        }
        if(match(T_TRUE)||match(T_FALSE)) return TYPE_BOOL;
        if(match(T_IDENTIFIER)) {
            string name=previous().lexeme;
            auto it=table.find(name);
            if(it==table.end()) {
                semanticError("use of undeclared identifier '" + name + "'", previous().line);
                return TYPE_ERROR;
            }
            return it->second.type;
        }
        if(match(T_LPAREN)) {
            ValueType t=parseExpression();
            if(!match(T_RPAREN)) syntaxError("expected ')'");
            return t;
        }
        syntaxError("expected expression");
        if(!check(T_END)) cur++;
        return TYPE_ERROR;
    }

    void declaration() {
        Token typeTok=peek();
        cur++;
        ValueType declared =
            typeTok.type==T_INT ? TYPE_INT :
            typeTok.type==T_FLOAT ? TYPE_FLOAT : TYPE_BOOL;

        if(!match(T_IDENTIFIER)) {
            syntaxError("expected identifier after type");
            synchronize();
            return;
        }

        Token id=previous();
        if(table.count(id.lexeme))
            semanticError("redeclaration of '" + id.lexeme + "'", id.line);
        else
            table[id.lexeme]={id.lexeme,declared,id.line};

        if(match(T_ASSIGN)) {
            ValueType rhs=parseExpression();
            if(rhs!=TYPE_ERROR && declared!=rhs) {
                semanticError("cannot assign " + typeName(rhs) +
                              " to variable '" + id.lexeme +
                              "' of type " + typeName(declared), id.line);
            }
        }

        if(!match(T_SEMICOLON)) {
            syntaxError("expected ';' after declaration");
            synchronize();
        }
    }

    void assignment() {
        Token id=peek();
        match(T_IDENTIFIER);

        auto it=table.find(id.lexeme);
        if(it==table.end())
            semanticError("assignment to undeclared identifier '" + id.lexeme + "'", id.line);

        if(!match(T_ASSIGN)) {
            syntaxError("expected '=' after identifier");
            synchronize();
            return;
        }

        ValueType rhs=parseExpression();
        if(it!=table.end() && rhs!=TYPE_ERROR && it->second.type!=rhs)
            semanticError("type mismatch in assignment to '" + id.lexeme + "'", id.line);

        if(!match(T_SEMICOLON)) {
            syntaxError("expected ';' after assignment");
            synchronize();
        }
    }

    void conditionStatement() {
        if(match(T_IF) || match(T_WHILE)) {
            int line=previous().line;
            if(!match(T_LPAREN)) syntaxError("expected '(' after condition keyword");
            ValueType cond=parseExpression();
            if(cond!=TYPE_ERROR && cond!=TYPE_BOOL)
                semanticError("condition must be boolean", line);
            if(!match(T_RPAREN)) syntaxError("expected ')' after condition");
            block();
        }
    }

    void block() {
        if(!match(T_LBRACE)) {
            syntaxError("expected '{'");
            return;
        }
        while(!check(T_RBRACE) && !check(T_END))
            statement();
        if(!match(T_RBRACE)) syntaxError("expected '}'");
    }

    void statement() {
        if(check(T_INT)||check(T_FLOAT)||check(T_BOOL)) declaration();
        else if(check(T_IDENTIFIER)) assignment();
        else if(check(T_IF)||check(T_WHILE)) conditionStatement();
        else {
            syntaxError("unexpected token '" + peek().lexeme + "'");
            synchronize();
        }
    }

public:
    explicit Parser(const vector<Token>& t):tokens(t){}

    bool parse() {
        while(!check(T_END)) statement();
        return syntaxOK;
    }

    const vector<string>& getErrors() const { return errors; }
    const unordered_map<string,Symbol>& getTable() const { return table; }
};

int main() {
    cout << "MiniLang Studio - Phase 1: Syntax and Semantic Analysis\n";
    cout << "Enter MiniLang source code. Type END on a separate line to finish.\n\n";

    string line, source;
    while(getline(cin,line)) {
        if(line=="END") break;
        source += line + "\n";
    }

    Lexer lexer(source);
    vector<Token> tokens=lexer.tokenize();

    cout << "TOKENS\n";
    for(const auto& t:tokens) {
        if(t.type==T_END) break;
        cout << t.line << "\t" << tokenName(t.type) << "\t" << t.lexeme << "\n";
    }

    for(const auto& t:tokens) {
        if(t.type==T_INVALID)
            cout << "Lexical error at line " << t.line
                 << ": invalid character '" << t.lexeme << "'\n";
    }

    Parser parser(tokens);
    bool syntaxOK=parser.parse();

    cout << "\nSYMBOL TABLE\n";
    cout << "Name\tType\tLine\n";
    for(const auto& item:parser.getTable())
        cout << item.second.name << "\t"
             << typeName(item.second.type) << "\t"
             << item.second.line << "\n";

    cout << "\nANALYSIS RESULT\n";
    if(parser.getErrors().empty() && syntaxOK)
        cout << "Syntax Analysis: PASSED\nSemantic Analysis: PASSED\n";
    else {
        cout << "Syntax Analysis: " << (syntaxOK ? "PASSED" : "FAILED") << "\n";
        cout << "Semantic Analysis: ";
        bool hasSemantic=false;
        for(const string& e:parser.getErrors())
            if(e.find("Semantic error")!=string::npos) hasSemantic=true;
        cout << (hasSemantic ? "FAILED" : "PASSED") << "\n";
        cout << "\nERRORS\n";
        for(const string& e:parser.getErrors()) cout << e << "\n";
    }

    return 0;
}
