package demo.great.config;

import javax.sql.DataSource;
import java.util.Map;

public class DynamicDataSource {
    private Map<Object, Object> targetDataSources;
    private Object defaultTargetDataSource;
    
    public void setTargetDataSources(Map<Object, Object> targetDataSources) {
        this.targetDataSources = targetDataSources;
    }
    
    public void setDefaultTargetDataSource(Object defaultTargetDataSource) {
        this.defaultTargetDataSource = defaultTargetDataSource;
    }
    
    protected Object determineCurrentLookupKey() {
        return DynamicDataSourceContextHolder.getDataSourceType();
    }
}