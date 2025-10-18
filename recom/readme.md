前端部分（frontend）：（没有太侧重去看，有点不清楚应该看什么重点）【10.2没有继续前端代码的查看】
npm install   # 第一次运行必须安装依赖
npm run dev   # 启动开发服务器
/frontend/src：
    app.vue：根组件
    /router/index.js：导航规则，当用户访问不同网址时，前端应用会渲染不同的 Vue 组件。
        Home.vue → 首页 /
        UserMatches.vue → 匹配列表 /matches
        MatchDetails.vue → 查看某两位用户的匹配详情 /match-details/:userId1/:userId2
        PairRecommendations.vue → 查看某两位用户的推荐结果 /recommendations/:userId1/:userId2
    /views/：页面视图（跟上述index.js连用）
    /services/：前端调用后端 API 的封装
        api.js：统一管理前端调用后端接口的方式，避免在每个 Vue 组件里都直接写 axios.get(...)

后端部分（app）：（9.29、9.30侧重）【10.2继续】
/app/core：
    /user_matching_engine.py：（root-2）
        class UserMatchingEngine：用户推荐与匹配(感觉有几个函数是没怎么用上的。。。。)(大部分已经厘清了)
    /recommendation_engine.py:（root-2）
        class RecommendationEngine：物品推荐与匹配(看了一部分了，到hybrid_recommend，这太绕了。。。。)【差不多看完了，但是还是有些细节不清楚，特别是里面有些代码多的模块，就感觉有点比较难。。。。。】
/app/models：
    /schemas.py：（root-2）不太懂干啥的，gpt说是规定了系统中“数据应该长什么样”【√，看是看了，但这玩意没看到有地方用啊。。。。。。。】
/app/utils：
    /data_loader.py：（root-2）把交互数据喂给推荐(√)
/app/api：
    /matching_api.py:（root-3）
        UserMatchingEngine包装，然后就可以调用【大部分看懂了】
    /recommendation_api.py：（root-3）
        RecommendationEngine包装，然后就可以调用【大部分看懂了】
    
交互：
/recom/main.py：入口（root-1）：感觉整个代码有点不对

requirements.txt：
fastapi uvicorn
numpy pandas
scikit-learn（conda）
torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

