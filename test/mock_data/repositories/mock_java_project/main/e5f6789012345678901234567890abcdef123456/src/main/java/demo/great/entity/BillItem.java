package demo.great.entity;

import demo.great.base.BaseEntity;
import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 账单项实体类
 * 
 * @author demo
 */
public class BillItem extends BaseEntity {
    
    private String title;
    private String description;
    private BigDecimal amount;
    private LocalDate billDate;
    private Long categoryId;
    private Long userId;
    
    // Constructors
    public BillItem() {}
    
    public BillItem(String title, BigDecimal amount, Long userId) {
        this.title = title;
        this.amount = amount;
        this.userId = userId;
    }
    
    // Getters and Setters
    public String getTitle() {
        return title;
    }
    
    public void setTitle(String title) {
        this.title = title;
    }
    
    public String getDescription() {
        return description;
    }
    
    public void setDescription(String description) {
        this.description = description;
    }
    
    public BigDecimal getAmount() {
        return amount;
    }
    
    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }
    
    public LocalDate getBillDate() {
        return billDate;
    }
    
    public void setBillDate(LocalDate billDate) {
        this.billDate = billDate;
    }
    
    public Long getCategoryId() {
        return categoryId;
    }
    
    public void setCategoryId(Long categoryId) {
        this.categoryId = categoryId;
    }
    
    public Long getUserId() {
        return userId;
    }
    
    public void setUserId(Long userId) {
        this.userId = userId;
    }
}