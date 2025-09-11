package demo.great.entity;

import java.util.Date;

public class User {
    private Integer id;
    private String username;
    private String nickname;
    private String password;
    private Date lastLoginTime;
    private Date lastBillTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getNickname() {
        return nickname;
    }

    public void setNickname(String nickname) {
        this.nickname = nickname;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public Date getLastLoginTime() {
        return lastLoginTime;
    }

    public void setLastLoginTime(Date lastLoginTime) {
        this.lastLoginTime = lastLoginTime;
    }

    public Date getLastBillTime() {
        return lastBillTime;
    }

    public void setLastBillTime(Date lastBillTime) {
        this.lastBillTime = lastBillTime;
    }
}
