package demo.great.dao;

import demo.great.entity.BillCategory;
import demo.great.dao.mapper.BillCategoryMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.List;

/**
 * 账单分类数据访问对象
 * 
 * @author demo
 */
@Repository
public class BillCategoryDao {
    
    @Autowired
    private BillCategoryMapper billCategoryMapper;
    
    public BillCategory findById(Long id) {
        return billCategoryMapper.selectById(id);
    }
    
    public List<BillCategory> findAll() {
        return billCategoryMapper.selectAll();
    }
    
    public BillCategory save(BillCategory category) {
        billCategoryMapper.insert(category);
        return category;
    }
    
    public BillCategory update(BillCategory category) {
        billCategoryMapper.update(category);
        return category;
    }
    
    public void deleteById(Long id) {
        billCategoryMapper.deleteById(id);
    }
    
    public BillCategory findByName(String name) {
        return billCategoryMapper.selectByName(name);
    }
}