#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# 交互式配置岗位描述
def configure_position_descriptions():
    print("\n===== 岗位描述 =====")
    print("请为职位输入详细描述（输入后按回车确认）\n")
    
    positions = {}
    # 为职位输入标题
    title = input("请输入职位标题: ").strip()
    
    # 为职位输入描述
    desc = input(f"请输入职位【{title}】的详细描述: ").strip()
    positions[title] = desc
    
    return positions

