package demo.great.base;

import java.util.List;

/**
 * 基础服务类
 * 
 * @author demo
 */
public abstract class BaseService<T extends BaseEntity> {
    
    /**
     * 根据ID查询实体
     */
    public abstract T findById(Long id);
    
    /**
     * 查询所有实体
     */
    public abstract List<T> findAll();
    
    /**
     * 保存实体
     */
    public abstract T save(T entity);
    
    /**
     * 根据ID删除实体
     */
    public abstract void deleteById(Long id);
    
    /**
     * 更新实体
     */
    public abstract T update(T entity);
}