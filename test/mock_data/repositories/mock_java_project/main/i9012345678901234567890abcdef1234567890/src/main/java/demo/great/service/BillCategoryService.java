package demo.great.service;

import demo.great.entity.BillCategory;
import demo.great.dao.BillCategoryDao;
import demo.great.base.BaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;

/**
 * 账单分类服务类
 * 
 * @author demo
 */
@Service
public class BillCategoryService extends BaseService<BillCategory> {
    
    @Autowired
    private BillCategoryDao billCategoryDao;
    
    @Override
    public BillCategory findById(Long id) {
        return billCategoryDao.findById(id);
    }
    
    @Override
    public List<BillCategory> findAll() {
        return billCategoryDao.findAll();
    }
    
    @Override
    public BillCategory save(BillCategory category) {
        // 业务逻辑验证
        if (category.getName() == null || category.getName().trim().isEmpty()) {
            throw new IllegalArgumentException("分类名称不能为空");
        }
        
        return billCategoryDao.save(category);
    }
    
    @Override
    public void deleteById(Long id) {
        billCategoryDao.deleteById(id);
    }
    
    @Override
    public BillCategory update(BillCategory category) {
        return billCategoryDao.update(category);
    }
}