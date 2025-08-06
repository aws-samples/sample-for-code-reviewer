package demo.great.base;

public class GreatException extends RuntimeException {
    public GreatException(String message) {
        super(message);
    }
    
    public GreatException(String message, Throwable cause) {
        super(message, cause);
    }
}