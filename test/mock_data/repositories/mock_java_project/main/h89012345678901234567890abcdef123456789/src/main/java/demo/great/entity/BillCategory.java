package demo.great.entity;

import demo.great.base.BaseEntity;

/**
 * 账单分类实体类
 * 
 * @author demo
 */
public class BillCategory extends BaseEntity {
    
    private String name;
    private String description;
    private String color;
    private Integer sortOrder;
    
    // Constructors
    public BillCategory() {}
    
    public BillCategory(String name, String description) {
        this.name = name;
        this.description = description;
    }
    
    // Getters and Setters
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public String getDescription() {
        return description;
    }
    
    public void setDescription(String description) {
        this.description = description;
    }
    
    public String getColor() {
        return color;
    }
    
    public void setColor(String color) {
        this.color = color;
    }
    
    public Integer getSortOrder() {
        return sortOrder;
    }
    
    public void setSortOrder(Integer sortOrder) {
        this.sortOrder = sortOrder;
    }
}