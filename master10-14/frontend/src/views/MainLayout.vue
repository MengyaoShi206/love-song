<template>
  <div class="layout">
    <!-- 左侧菜单 -->
    <aside class="sidebar">
      <el-card class="sidebar-card" shadow="never">
        <div class="brand">
          <el-avatar :size="42" :src="display.user_account?.avatar_url || ''" />
          <div class="brand-meta">
            <div class="brand-title">个人中心</div>
            <div class="brand-sub">完善资料更易匹配</div>
          </div>
        </div>

        <el-menu
          :default-active="defaultActive"
          class="pretty-menu"
          @select="onSelect"
          :router="false"
        >
          <el-menu-item index="display">
            <el-icon><User /></el-icon>
            <span>资料展示</span>
          </el-menu-item>
          <el-menu-item index="other" disabled>
            <el-icon><Setting /></el-icon>
            <span>其他（待扩展）</span>
          </el-menu-item>
        </el-menu>
      </el-card>
    </aside>

    <!-- 右侧内容 -->
    <main class="content">
      <!-- 顶部：完善度 + 编辑 -->
      <div class="topbar">
        <div class="topbar-left">
          <div class="topbar-title">资料完整度</div>
          <el-progress
            :percentage="completion"
            :status="completionStatus"
            :stroke-width="16"
            style="width: 240px"
          />
          <span class="font-medium text-gray-700">{{ completion }}</span>
          <el-tag type="info" class="topbar-tag">
            媒体已审 {{ display.media_count }} · Q&A {{ display.qna_count }}
          </el-tag>
        </div>
        
        <div v-if="display.plan_code" class="vip-line">
          <el-tag :type="vipTagType" size="media">
            会员等级：{{ display.plan_code }}
          </el-tag>
        </div>

        <div class="topbar-actions">
          <el-button v-if="!editMode" type="primary" @click="enterEdit">编辑</el-button>
          <template v-else>
            <el-button type="success" :loading="saving" @click="save">保存</el-button>
            <el-button @click="cancel">取消</el-button>
          </template>
        </div>
      </div>

      <!-- 折叠面板 -->
      <el-collapse v-model="activeNames" class="panel">
        <!-- 1. 基础信息 -->
        <el-collapse-item title="基础信息" name="1">
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户名">{{ display.user_account?.username }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ display.user_account?.nickname }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ display.user_account?.phone }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ display.user_account?.email }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ display.user_account?.gender }}</el-descriptions-item>
              <el-descriptions-item label="城市">{{ display.user_account?.city }}</el-descriptions-item>
              <el-descriptions-item label="头像链接">{{ display.user_account?.avatar_url }}</el-descriptions-item>
            </el-descriptions>
          </template>

          <!-- 编辑模式 -->
          <template v-else>
            <el-form :model="display.user_account" label-width="100px" style="max-width: 500px">
              <el-form-item label="昵称">
                <el-input v-model="display.user_account.nickname" placeholder="输入昵称" />
              </el-form-item>
              <el-form-item label="手机号">
                <el-input v-model="display.user_account.phone" placeholder="11位手机号" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="display.user_account.email" placeholder="电子邮箱" />
              </el-form-item>
              <el-form-item label="性别">
                <el-select v-model="display.user_account.gender" placeholder="选择性别">
                  <el-option label="男" value="male" />
                  <el-option label="女" value="female" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="城市">
                <el-input v-model="display.user_account.city" placeholder="所在城市" />
              </el-form-item>
              <el-form-item label="头像URL">
                <el-input v-model="display.user_account.avatar_url" placeholder="头像链接" />
              </el-form-item>
            </el-form>
          </template>
        </el-collapse-item>


        <!-- 2. 公开资料 -->
        <el-collapse-item title="公开资料" name="2">
          <template v-if="!editMode">
            <div class="pub-item"><b>个性签名：</b>{{ display.user_profile_public?.tagline || '—' }}</div>
            <div class="pub-item"><b>自我介绍：</b></div>
            <div class="pub-bio">{{ display.user_profile_public?.bio || '—' }}</div>
          </template>
          <template v-else>
            <el-form :model="display.user_profile_public" label-width="100px" style="max-width: 500px">
              <el-form-item label="个性签名"><el-input v-model="display.user_profile_public.tagline" /></el-form-item>
              <el-form-item label="自我介绍">
                <el-input
                  type="textarea"
                  v-model="display.user_profile_public.bio"
                  :rows="5"
                  placeholder="介绍自己"
                />
              </el-form-item>
            </el-form>
          </template>
        </el-collapse-item>

        <!-- 3. 择偶意向 -->
        <el-collapse-item title="择偶意向" name="3">
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="感情目标">{{ display.user_intention?.relationship_goal }}</el-descriptions-item>
              <el-descriptions-item label="年龄">{{ display.user_intention?.preferred_age_min }} - {{ display.user_intention?.preferred_age_max }}</el-descriptions-item>
              <el-descriptions-item label="身高">{{ display.user_intention?.preferred_height_min }} - {{ display.user_intention?.preferred_height_max }}</el-descriptions-item>
              <el-descriptions-item label="偏好城市">{{ display.user_intention?.preferred_cities }}</el-descriptions-item>
              <el-descriptions-item label="接受异地">{{ display.user_intention?.accept_long_distance ? '是' : '否' }}</el-descriptions-item>
              <el-descriptions-item label="接受离异">{{ display.user_intention?.accept_divorce ? '是' : '否' }}</el-descriptions-item>
              <el-descriptions-item label="接受子女">{{ display.user_intention?.accept_children ? '是' : '否' }}</el-descriptions-item>
              <el-descriptions-item label="结婚期望">{{ display.user_intention?.marriage_timeline }}</el-descriptions-item>
              <el-descriptions-item label="生育计划">{{ display.user_intention?.child_plan }}</el-descriptions-item>
              <el-descriptions-item label="宗教信仰">{{ display.user_intention?.religion }}</el-descriptions-item>
            </el-descriptions>
          </template>
          <template v-else>
            <el-form :model="display.user_intention" label-width="120px" style="max-width: 600px">
              <el-form-item label="感情目标">
                <el-select v-model="display.user_intention.relationship_goal">
                  <el-option label="恋爱" value="dating" />
                  <el-option label="结婚" value="marriage" />
                </el-select>
              </el-form-item>
              <el-form-item label="年龄范围">
                <el-input v-model="display.user_intention.preferred_age_min" style="width: 90px" /> -
                <el-input v-model="display.user_intention.preferred_age_max" style="width: 90px" />
              </el-form-item>
              <el-form-item label="偏好城市"><el-input v-model="display.user_intention.preferred_cities" /></el-form-item>
              <el-form-item label="宗教信仰"><el-input v-model="display.user_intention.religion" /></el-form-item>
            </el-form>
          </template>
        </el-collapse-item>

        <!-- 4. 生活方式 -->
        <el-collapse-item title="生活方式" name="4">
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="作息">{{ display.user_lifestyle?.schedule }}</el-descriptions-item>
              <el-descriptions-item label="饮酒">{{ display.user_lifestyle?.drinking }}</el-descriptions-item>
              <el-descriptions-item label="吸烟">{{ display.user_lifestyle?.smoking }}</el-descriptions-item>
              <el-descriptions-item label="锻炼">{{ display.user_lifestyle?.workout_freq }}</el-descriptions-item>
              <el-descriptions-item label="饮食">{{ display.user_lifestyle?.diet }}</el-descriptions-item>
              <el-descriptions-item label="宠物">{{ display.user_lifestyle?.pet_view }}</el-descriptions-item>
              <el-descriptions-item label="性格">{{ display.user_lifestyle?.personality }}</el-descriptions-item>
            </el-descriptions>
          </template>
          <template v-else>
            <el-form :model="display.user_lifestyle" label-width="120px" style="max-width: 600px">
              <el-form-item label="作息">
                <el-select v-model="display.user_lifestyle.schedule">
                  <el-option label="早睡早起" value="early" />
                  <el-option label="正常作息" value="normal" />
                  <el-option label="晚睡晚起" value="late" />
                </el-select>
              </el-form-item>
              <el-form-item label="饮酒"><el-select v-model="display.user_lifestyle.drinking"><el-option label="从不" value="never" /><el-option label="偶尔" value="occasionally" /><el-option label="经常" value="often" /></el-select></el-form-item>
              <el-form-item label="吸烟"><el-select v-model="display.user_lifestyle.smoking"><el-option label="从不" value="never" /><el-option label="偶尔" value="occasionally" /><el-option label="经常" value="often" /></el-select></el-form-item>
              <el-form-item label="锻炼频率"><el-select v-model="display.user_lifestyle.workout_freq"><el-option label="无" value="none" /><el-option label="每周" value="weekly" /><el-option label="3次以上" value="3+weekly" /><el-option label="每天" value="daily" /></el-select></el-form-item>
              <el-form-item label="饮食习惯"><el-input v-model="display.user_lifestyle.diet" /></el-form-item>
              <el-form-item label="性格"><el-input v-model="display.user_lifestyle.personality" /></el-form-item>
            </el-form>
          </template>
        </el-collapse-item>

        <!-- 5. 问答展示 -->
        <el-collapse-item title="问答展示" name="5">
          <!-- 非编辑模式 -->
          <template v-if="!editMode">
            <div v-if="display.user_qna?.length">
              <div v-for="(item, i) in display.user_qna" :key="i" class="qna-item">
                <b>Q{{ i + 1 }}：{{ item.question }}</b>
                <p>A：{{ item.answer || '—' }}</p>
              </div>
            </div>
            <div v-else class="text-gray-500">暂无公开问答</div>
          </template>

          <!-- 编辑模式 -->
          <template v-else>
            <div v-for="(item, i) in editableQna" :key="i" class="qna-item">
              <div class="flex items-center justify-between">
                <b>Q{{ i + 1 }}：{{ item.question }}</b>
                <el-button type="danger" link size="small" @click="removeQna(i)">删除</el-button>
              </div>
              <el-input
                v-model="item.answer"
                type="textarea"
                :rows="2"
                placeholder="请输入你的回答"
                style="margin-top: 6px"
              />
            </div>

            <el-divider>系统推荐问题</el-divider>

            <el-select v-model="selectedTemplate" placeholder="选择一个系统问题" style="width: 280px">
              <el-option v-for="(q, i) in questionTemplates" :key="i" :label="q" :value="q" />
            </el-select>
            <el-button type="primary" size="small" @click="addQnaFromTemplate">添加</el-button>
          </template>
        </el-collapse-item>

      </el-collapse>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue' 
import { useRouter } from 'vue-router' 
import { ElMessage } from 'element-plus' 
import { User, Setting } from '@element-plus/icons-vue' 
import { getDisplay, updateProfile } from '@/api' 

const routeUid = Number(new URLSearchParams(location.search).get('uid') || 0) 
const uid = Number(localStorage.getItem('uid') || routeUid || 1) 
const router = useRouter() 
const defaultActive = ref('display') 

const onSelect = (key) => { 
  if (key === 'display') router.push('/main') 
}

const display = reactive({
  user_account: {},
  user_profile_public: {},
  user_intention: {},
  user_lifestyle: {},
  user_qna: [],
  media_count: 0,
  qna_count: 0
})

const editMode = ref(false)
const saving = ref(false)
const activeNames = ref(['1', '2', '3', '4', '5'])

const completion = computed(() => Number(display.user_profile_public?.completion_score || 0))
const completionStatus = computed(() => {
  const code = display.plan_code
  if (!code) return '普通用户'
  if (code === 'vip_plus') return 'VIP+'
  if (code === 'vip') return 'VIP'
  return code.toUpperCase()
})

const vipTagType = computed(() => {
  if (display.plan_code === 'vip_plus') return 'danger'
  if (display.plan_code === 'vip') return 'warning'
  return 'info'
})

const questionTemplates = [
  '你理想的约会方式？',
  '你最喜欢的电影类型？',
  '你最喜欢的旅行目的地？',
  '三年内的计划？'
]

const selectedTemplate = ref('')
const editableQna = ref([])

function removeQna(index) {
  editableQna.value.splice(index, 1)
}

function addQnaFromTemplate() {
  if (!selectedTemplate.value) {
    ElMessage.warning('请选择一个问题')
    return
  }
  // 检查是否重复
  if (editableQna.value.some(q => q.question === selectedTemplate.value)) {
    ElMessage.warning('该问题已存在')
    return
  }
  editableQna.value.push({ question: selectedTemplate.value, answer: '' })
  selectedTemplate.value = ''
}



async function load() {
  try {
    const res = await getDisplay(uid)
    if (res && res.data) {
      Object.assign(display, res.data)
      editableQna.value = JSON.parse(JSON.stringify(display.user_qna || []))
    } else {
      ElMessage.error('加载用户数据失败：返回为空')
    }
  } catch (e) {
    console.error('❌ 加载用户资料失败:', e)
    ElMessage.error('无法加载用户资料，请检查后端是否启动')
  }
}


function enterEdit() {
  editMode.value = true
}
function cancel() {
  editMode.value = false
}
async function save() {
  try {
    saving.value = true
    const payload = {
      ...display.user_account,
      ...display.user_profile_public,
      ...display.user_intention,
      ...display.user_lifestyle,
      user_qna: editableQna.value.filter(q => q.answer && q.answer.trim() !== "")
    }
    console.log("🟢 即将提交 payload:", payload)
    const res = await updateProfile(uid, payload)
    console.log("✅ 更新成功:", res.data)
    ElMessage.success('资料已更新并重算完善度')
    editMode.value = false
    await load()
  } catch (e) {
    console.error("❌ 更新失败:", e)
    ElMessage.error(e?.response?.data?.detail || e.message || '更新失败')
  } finally {
    saving.value = false
  }
}



onMounted(load)
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: #f8fafc;
}
.sidebar {
  width: 264px;
  padding: 14px;
  background: linear-gradient(180deg, #f8fafc, #ffffff);
  border-right: 1px solid #eef2f7;
}
.content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}
.sidebar-card {
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: saturate(160%) blur(8px);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.brand-title {
  font-weight: 600;
  color: #1f2937;
}
.brand-sub {
  color: #6b7280;
  font-size: 12px;
}
.pretty-menu {
  border-right: 0 !important;
  background: transparent !important;
  --menu-item-radius: 12px;
}
:deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 6px 0;
  border-radius: var(--menu-item-radius);
  font-weight: 500;
  color: #4b5563;
  transition: all 0.2s ease;
}
:deep(.el-menu-item:hover) {
  background: #f1f5f9;
}
:deep(.el-menu-item.is-active) {
  background: #eef2ff;
  color: #111827;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.pub-item {
  margin-bottom: 6px;
}
.pub-bio {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;
}
.qna-item {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 8px;
}
.vip-line {
  margin-top: 6px;
}
.qna-item {
  margin-bottom: 12px;
  padding: 8px 10px;
  background: #f9fafb;
  border-radius: 8px;
}
.el-divider {
  margin: 10px 0;
  color: #9ca3af;
}

</style>
