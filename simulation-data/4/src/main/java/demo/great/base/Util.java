package demo.great.base;

import demo.great.entity.User;
import java.util.HashMap;
import java.util.Map;

public class Util {

    /**
     * 将User对象转换为Map
     * @param user 需要转换的User对象
     * @return 转换后的Map
     */
    public static Map<String, Object> toMap(User user) {
        Map<String, Object> resultMap = new HashMap<>();
        
        if (user == null) {
            return resultMap;
        }

        // 将User对象的属性添加到Map中
        addToMap(resultMap, "id", user.getId());
        addToMap(resultMap, "username", user.getUsername());
        addToMap(resultMap, "nickname", user.getNickname());
        addToMap(resultMap, "password", user.getPassword());
        addToMap(resultMap, "lastLoginTime", user.getLastLoginTime());
        addToMap(resultMap, "lastBillTime", user.getLastBillTime());

        return resultMap;
    }

    /**
     * 辅助方法：如果值不为null，则添加到Map中
     */
    private static void addToMap(Map<String, Object> map, String key, Object value) {
        if (value != null) {
            map.put(key, value);
        }
    }
}

