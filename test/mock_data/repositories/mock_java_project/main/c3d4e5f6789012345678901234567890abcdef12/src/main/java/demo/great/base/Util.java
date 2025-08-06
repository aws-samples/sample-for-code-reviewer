package demo.great.base;

public class Util {
    public static String formatString(String input) {
        return input != null ? input.trim() : "";
    }
    
    public static boolean isEmpty(String str) {
        return str == null || str.trim().isEmpty();
    }
}