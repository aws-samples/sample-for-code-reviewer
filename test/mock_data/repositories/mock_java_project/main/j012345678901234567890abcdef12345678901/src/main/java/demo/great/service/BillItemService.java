package demo.great.service;

import demo.great.entity.BillItem;
import demo.great.dao.BillItemDao;
import demo.great.base.BaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;
import java.math.BigDecimal;

/**
 * 账单项服务类
 * 
 * @author demo
 */
@Service
public class BillItemService extends BaseService<BillItem> {
    
    @Autowired
    private BillItemDao billItemDao;
    
    @Override
    public BillItem findById(Long id) {
        return billItemDao.findById(id);
    }
    
    @Override
    public List<BillItem> findAll() {
        return billItemDao.findAll();
    }
    
    @Override
    public BillItem save(BillItem item) {
        // 业务逻辑验证
        if (item.getTitle() == null || item.getTitle().trim().isEmpty()) {
            throw new IllegalArgumentException("账单标题不能为空");
        }
        
        if (item.getAmount() == null || item.getAmount().compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("金额不能为负数");
        }
        
        return billItemDao.save(item);
    }
    
    @Override
    public void deleteById(Long id) {
        billItemDao.deleteById(id);
    }
    
    @Override
    public BillItem update(BillItem item) {
        return billItemDao.update(item);
    }
}