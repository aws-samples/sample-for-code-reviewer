package demo.great.config;

public class DynamicDataSourceContextHolder {

    private static final ThreadLocal<DynamicDataSourceType> CONTEXT = new ThreadLocal<>();

    public static void setDataSourceType(DynamicDataSourceType dataSourceType) {
        CONTEXT.set(dataSourceType);
    }

    public static DynamicDataSourceType getDataSourceType() {
        return CONTEXT.get() == null ? DynamicDataSourceType.MASTER : CONTEXT.get();
    }

    public static void clearDataSourceType() {
        CONTEXT.remove();
    }

    public enum DynamicDataSourceType {
        MASTER,
        SLAVE
    }
}
