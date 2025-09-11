package demo.great.dao.mapper;

import demo.great.entity.BillItem;
import org.apache.ibatis.annotations.Mapper;

import java.util.Date;
import java.util.List;

@Mapper
public interface BillItemMapper {
    int createItem(BillItem item);
    int updateItem(BillItem item);
    int deleteItem(Integer id);
    BillItem loadItem(Integer id);
    List<BillItem> listItems(Integer userId, Integer categoryId, Date startDate, Date endDate, String billType);
}
