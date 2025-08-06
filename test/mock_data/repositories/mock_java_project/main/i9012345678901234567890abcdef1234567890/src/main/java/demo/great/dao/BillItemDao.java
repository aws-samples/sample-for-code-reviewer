package demo.great.dao;

import demo.great.entity.BillItem;
import demo.great.dao.mapper.BillItemMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.List;

/**
 * 账单项数据访问对象
 * 
 * @author demo
 */
@Repository
public class BillItemDao {
    
    @Autowired
    private BillItemMapper billItemMapper;
    
    public BillItem findById(Long id) {
        return billItemMapper.selectById(id);
    }
    
    public List<BillItem> findAll() {
        return billItemMapper.selectAll();
    }
    
    public BillItem save(BillItem item) {
        billItemMapper.insert(item);
        return item;
    }
    
    public BillItem update(BillItem item) {
        billItemMapper.update(item);
        return item;
    }
    
    public void deleteById(Long id) {
        billItemMapper.deleteById(id);
    }
    
    public List<BillItem> findByUserId(Long userId) {
        return billItemMapper.selectByUserId(userId);
    }
    
    public List<BillItem> findByCategoryId(Long categoryId) {
        return billItemMapper.selectByCategoryId(categoryId);
    }
}