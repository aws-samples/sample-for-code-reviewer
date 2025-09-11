package demo.great.config;

public class DataSourceContextHolder {
    private static final ThreadLocal<DataSourceType> CONTEXT = new ThreadLocal<>();

    public static void write() {
        setDataSourceType(DataSourceType.MASTER);
    }

    public static void read() {
        setDataSourceType(DataSourceType.SLAVE);
    }

    public static void setDataSourceType(DataSourceType dataSourceType) {
        CONTEXT.set(dataSourceType);
    }

    public static DataSourceType getDataSourceType() {
        return CONTEXT.get() == null ? DataSourceType.MASTER : CONTEXT.get();
    }

    public static void clearDataSourceType() {
        CONTEXT.remove();
    }

    public enum DataSourceType {
        MASTER,
        SLAVE
    }
}
