package com.ruoyi.system.domain;

/**
 * 阀井数据对象：承载从 biz_valve_well 表查询出来的一行记录。
 *
 * 一行记录对应一个 ValveWell，多行记录对应 List<ValveWell>。
 * 可以类比前端的一个对象，但 Java 类还在运行时参与对象创建。
 * 不继承 BaseEntity，是因为这个最小示例只需要以下六个属性。
 * XML 中的 resultMap 负责将数据库下划线列名映射到这里的驼峰属性名。
 */
public class ValveWell
{
    /** 内部主键，例如 1；用于唯一标识数据库记录。 */
    private Long wellId;

    /** 工作人员看到的业务编号，例如 FJ001，与内部主键不是同一概念。 */
    private String wellCode;

    /** 阀井名称，例如人民路一号阀井。 */
    private String wellName;

    /** 所在位置的文字描述，本例不涉及坐标或空间查询。 */
    private String location;

    /** 阀门口径，单位为毫米；JSON 返回数字 200，展示单位由前端处理。 */
    private Integer diameter;

    /** 状态编码：字符串 0 表示正常，字符串 1 表示停用。 */
    private String status;

    // getter 用于读取属性，setter 用于写入属性。
    // MyBatis 映射查询结果时可通过这些 setter 填充对象；
    // Jackson 输出 JSON 时会读取这些 getter，得到 wellId、wellCode 等字段。
    public Long getWellId()
    {
        return wellId;
    }

    public void setWellId(Long wellId)
    {
        this.wellId = wellId;
    }

    public String getWellCode()
    {
        return wellCode;
    }

    public void setWellCode(String wellCode)
    {
        this.wellCode = wellCode;
    }

    public String getWellName()
    {
        return wellName;
    }

    public void setWellName(String wellName)
    {
        this.wellName = wellName;
    }

    public String getLocation()
    {
        return location;
    }

    public void setLocation(String location)
    {
        this.location = location;
    }

    public Integer getDiameter()
    {
        return diameter;
    }

    public void setDiameter(Integer diameter)
    {
        this.diameter = diameter;
    }

    public String getStatus()
    {
        return status;
    }

    public void setStatus(String status)
    {
        this.status = status;
    }
}
