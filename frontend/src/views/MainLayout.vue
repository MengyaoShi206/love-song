<!-- /frontend/src/views/MainLayout.vue -->
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

          <el-menu-item index="match">
            <el-icon><User /></el-icon>
            <span>匹配资料展示</span>
          </el-menu-item>

          <el-menu-item index="chat">
            <el-icon><ChatLineSquare /></el-icon>
            <span class="menu-chat-label">
              聊天（已匹配）
              <span v-if="totalUnread > 0" class="menu-unread-pill">
                {{ totalUnreadDisplay }}
              </span>
            </span>
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
      <!-- 顶部栏：完善度 + 会员 + 计数 -->
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
          <el-tag :type="vipTagType" size="medium">
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
          <!-- 查看态 -->
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户名">{{ display.user_account?.username || '—' }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ display.user_account?.nickname || '—' }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ maskPhone(display.user_account?.phone) }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ maskEmail(display.user_account?.email) }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ display.user_account?.gender || '—' }}</el-descriptions-item>
              <el-descriptions-item label="城市">{{ display.user_account?.city || '—' }}</el-descriptions-item>
              <el-descriptions-item label="生日">{{ display.user_account?.birth_date || '—' }}</el-descriptions-item>
              <el-descriptions-item label="年龄">{{ calcAge(display.user_account?.birth_date) ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="身高">
                {{ numOrDash(display.user_account?.height_cm) }}<span v-if="display.user_account?.height_cm"> cm</span>
              </el-descriptions-item>
              <el-descriptions-item label="体重">
                {{ numOrDash(display.user_account?.weight_kg) }}<span v-if="display.user_account?.weight_kg"> kg</span>
              </el-descriptions-item>
              <el-descriptions-item label="家乡">{{ display.user_account?.hometown || '—' }}</el-descriptions-item>
              <el-descriptions-item label="感情状态">{{ display.user_account?.marital_status || '—' }}</el-descriptions-item>
              <el-descriptions-item label="是否有子女">{{ yn(display.user_account?.has_children) }}</el-descriptions-item>
              <el-descriptions-item label="头像链接">
                <template v-if="display.user_account?.avatar_url">
                  <a :href="display.user_account.avatar_url" target="_blank" rel="noopener">{{ display.user_account.avatar_url }}</a>
                  <div style="margin-top:6px">
                    <el-avatar :size="40" :src="display.user_account.avatar_url" />
                  </div>
                </template>
                <span v-else>—</span>
              </el-descriptions-item>
            </el-descriptions>
          </template>

          <!-- 编辑态 -->
          <template v-else>
            <el-form
              ref="accountFormRef"
              :model="display.user_account"
              :rules="accountRules"
              label-width="100px"
              style="max-width: 680px"
            >
              <div class="form-grid">
                <el-form-item label="昵称" prop="nickname">
                  <el-input v-model="display.user_account.nickname" placeholder="输入昵称" maxlength="30" />
                </el-form-item>

                <el-form-item label="性别" prop="gender">
                  <el-select v-model="display.user_account.gender" placeholder="选择性别" clearable>
                    <el-option label="男" value="male" />
                    <el-option label="女" value="female" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>

                <el-form-item label="手机号" prop="phone">
                  <el-input v-model="display.user_account.phone" placeholder="11位手机号" maxlength="20" />
                </el-form-item>

                <el-form-item label="邮箱" prop="email">
                  <el-input v-model="display.user_account.email" placeholder="电子邮箱" maxlength="80" />
                </el-form-item>

                <el-form-item label="城市" prop="city">
                  <el-input v-model="display.user_account.city" placeholder="所在城市" />
                </el-form-item>

                <el-form-item label="家乡" prop="hometown">
                  <el-input v-model="display.user_account.hometown" placeholder="籍贯/家乡" />
                </el-form-item>

                <el-form-item label="生日" prop="birth_date">
                  <el-date-picker
                    v-model="display.user_account.birth_date"
                    type="date"
                    placeholder="选择日期"
                    value-format="YYYY-MM-DD"
                    style="width: 100%"
                  />
                </el-form-item>

                <el-form-item label="身高(cm)" prop="height_cm">
                  <el-input-number v-model="display.user_account.height_cm" :min="120" :max="230" :step="1" controls-position="right" />
                </el-form-item>

                <el-form-item label="体重(kg)" prop="weight_kg">
                  <el-input-number v-model="display.user_account.weight_kg" :min="35" :max="150" :step="1" controls-position="right" />
                </el-form-item>

                <el-form-item label="感情状态" prop="marital_status">
                  <el-select v-model="display.user_account.marital_status" placeholder="请选择" clearable>
                    <el-option label="未婚" value="single" />
                    <el-option label="离异" value="divorced" />
                    <el-option label="丧偶" value="widowed" />
                  </el-select>
                </el-form-item>

                <el-form-item label="有子女" prop="has_children">
                  <el-switch v-model="display.user_account.has_children" />
                </el-form-item>

                <el-form-item label="头像URL" prop="avatar_url" class="avatar-row">
                  <div class="avatar-input">
                    <el-input v-model="display.user_account.avatar_url" placeholder="https://..." />
                    <el-avatar
                      v-if="display.user_account.avatar_url"
                      :src="display.user_account.avatar_url"
                      :size="40"
                      style="margin-left:8px"
                    />
                  </div>
                </el-form-item>
              </div>
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
              <el-form-item label="个性签名">
                <el-input v-model="display.user_profile_public.tagline" />
              </el-form-item>
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
          <!-- 查看态 -->
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="感情目标">{{ goalText(display.user_intention?.relationship_goal) }}</el-descriptions-item>
              <el-descriptions-item label="年龄">
                {{ numOrDash(display.user_intention?.preferred_age_min) }} - {{ numOrDash(display.user_intention?.preferred_age_max) }}
              </el-descriptions-item>
              <el-descriptions-item label="身高">
                {{ numOrDash(display.user_intention?.preferred_height_min) }} - {{ numOrDash(display.user_intention?.preferred_height_max) }}
              </el-descriptions-item>
              <el-descriptions-item label="偏好城市">{{ displayCities(display.user_intention?.preferred_cities) }}</el-descriptions-item>
              <el-descriptions-item label="接受异地">{{ yn(display.user_intention?.accept_long_distance) }}</el-descriptions-item>
              <el-descriptions-item label="接受离异">{{ yn(display.user_intention?.accept_divorce) }}</el-descriptions-item>
              <el-descriptions-item label="接受子女">{{ yn(display.user_intention?.accept_children) }}</el-descriptions-item>
              <el-descriptions-item label="结婚期望">{{ timelineText(display.user_intention?.marriage_timeline) }}</el-descriptions-item>
              <el-descriptions-item label="生育计划">{{ childPlanText(display.user_intention?.child_plan) }}</el-descriptions-item>
              <el-descriptions-item label="宗教信仰">{{ display.user_intention?.religion || '—' }}</el-descriptions-item>
              <el-descriptions-item label="家庭观">{{ familyViewText(display.user_intention?.family_view) }}</el-descriptions-item>
            </el-descriptions>
          </template>

          <!-- 编辑态 -->
          <template v-else>
            <el-form
              ref="intentionFormRef"
              :model="display.user_intention"
              :rules="intentionRules"
              label-width="120px"
              style="max-width: 720px"
            >
              <div class="form-grid">
                <el-form-item label="感情目标" prop="relationship_goal">
                  <el-select v-model="display.user_intention.relationship_goal">
                    <el-option label="恋爱" value="dating" />
                    <el-option label="结婚" value="marriage" />
                  </el-select>
                </el-form-item>

                <el-form-item label="年龄范围" prop="age_range">
                  <div class="inline-range">
                    <el-input-number
                      v-model="display.user_intention.preferred_age_min"
                      :min="18" :max="70" :step="1" controls-position="right"
                    />
                    <span class="mx-6">—</span>
                    <el-input-number
                      v-model="display.user_intention.preferred_age_max"
                      :min="18" :max="70" :step="1" controls-position="right"
                    />
                  </div>
                </el-form-item>

                <el-form-item label="身高范围(cm)" prop="height_range">
                  <div class="inline-range">
                    <el-input-number v-model="display.user_intention.preferred_height_min" :min="140" :max="220" />
                    <span class="mx-6">—</span>
                    <el-input-number v-model="display.user_intention.preferred_height_max" :min="140" :max="220" />
                  </div>
                </el-form-item>

                <el-form-item label="偏好城市" prop="preferred_cities">
                  <el-input
                    v-model="citiesInput"
                    placeholder="多城市用中文/英文逗号分隔，例如：北京, 上海, 深圳"
                  />
                  <div class="hint">保存时会转为数组：["北京","上海","深圳"]</div>
                </el-form-item>

                <el-form-item label="接受异地" prop="accept_long_distance">
                  <el-switch v-model="display.user_intention.accept_long_distance" />
                </el-form-item>

                <el-form-item label="接受离异" prop="accept_divorce">
                  <el-switch v-model="display.user_intention.accept_divorce" />
                </el-form-item>

                <el-form-item label="接受子女" prop="accept_children">
                  <el-switch v-model="display.user_intention.accept_children" />
                </el-form-item>

                <el-form-item label="结婚期望" prop="marriage_timeline">
                  <el-select v-model="display.user_intention.marriage_timeline" clearable placeholder="请选择">
                    <el-option label="1年内" value="1y" />
                    <el-option label="2年内" value="2y" />
                    <el-option label="随时" value="flexible" />
                    <el-option label="暂不考虑" value="unknown" />
                  </el-select>
                </el-form-item>

                <el-form-item label="生育计划" prop="child_plan">
                  <el-select v-model="display.user_intention.child_plan" clearable placeholder="请选择">
                    <el-option label="尽快" value="want" />
                    <el-option label="合适再说" value="flexible" />
                    <el-option label="不考虑" value="dont_want" />
                    <el-option label="未决定" value="unknown" />
                  </el-select>
                </el-form-item>

                <el-form-item label="宗教信仰" prop="religion">
                  <el-input v-model="display.user_intention.religion" placeholder="可留空" />
                </el-form-item>

                <el-form-item label="家庭观" prop="family_view">
                  <el-select v-model="display.user_intention.family_view" clearable placeholder="请选择">
                    <el-option label="自己住" value="independent" />
                    <el-option label="和父母住" value="with_parents" />
                    <el-option label="随意" value="flexible" />
                  </el-select>
                </el-form-item>
              </div>
            </el-form>
          </template>
        </el-collapse-item>

        <!-- 4. 生活方式 -->
        <el-collapse-item title="生活方式" name="4">
          <!-- 查看态 -->
          <template v-if="!editMode">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="作息">{{ scheduleText(display.user_lifestyle?.schedule) }}</el-descriptions-item>
              <el-descriptions-item label="饮酒">{{ drinkingText(display.user_lifestyle?.drinking) }}</el-descriptions-item>
              <el-descriptions-item label="吸烟">{{ smokingText(display.user_lifestyle?.smoking) }}</el-descriptions-item>
              <el-descriptions-item label="锻炼">{{ workoutText(display.user_lifestyle?.workout_freq) }}</el-descriptions-item>
              <el-descriptions-item label="饮食">{{ display.user_lifestyle?.diet || '—' }}</el-descriptions-item>
              <el-descriptions-item label="宠物">{{ petText(display.user_lifestyle?.pet_view) }}</el-descriptions-item>
              <el-descriptions-item label="消费观">{{ spendingText(display.user_lifestyle?.spending_view) }}</el-descriptions-item>
              <el-descriptions-item label="储蓄观">{{ savingText(display.user_lifestyle?.saving_view) }}</el-descriptions-item>
              <el-descriptions-item label="旅行偏好">{{ listOrDash(display.user_lifestyle?.travel_pref) }}</el-descriptions-item>
              <el-descriptions-item label="兴趣标签">{{ listOrDash(display.user_lifestyle?.interests) }}</el-descriptions-item>
              <el-descriptions-item label="性格">{{ display.user_lifestyle?.personality || '—' }}</el-descriptions-item>
            </el-descriptions>
          </template>

          <!-- 编辑态 -->
          <template v-else>
            <el-form
              ref="lifestyleFormRef"
              :model="display.user_lifestyle"
              :rules="lifestyleRules"
              label-width="120px"
              style="max-width: 720px"
            >
              <div class="form-grid">
                <el-form-item label="作息" prop="schedule">
                  <el-select v-model="display.user_lifestyle.schedule" placeholder="请选择" clearable>
                    <el-option label="早睡早起" value="early" />
                    <el-option label="正常作息" value="normal" />
                    <el-option label="晚睡晚起" value="late" />
                  </el-select>
                </el-form-item>

                <el-form-item label="饮酒" prop="drinking">
                  <el-select v-model="display.user_lifestyle.drinking" placeholder="请选择" clearable>
                    <el-option label="从不" value="never" />
                    <el-option label="偶尔" value="occasionally" />
                    <el-option label="经常" value="often" />
                  </el-select>
                </el-form-item>

                <el-form-item label="吸烟" prop="smoking">
                  <el-select v-model="display.user_lifestyle.smoking" placeholder="请选择" clearable>
                    <el-option label="从不" value="never" />
                    <el-option label="偶尔" value="occasionally" />
                    <el-option label="经常" value="often" />
                  </el-select>
                </el-form-item>

                <el-form-item label="锻炼频率" prop="workout_freq">
                  <el-select v-model="display.user_lifestyle.workout_freq" placeholder="请选择" clearable>
                    <el-option label="无" value="none" />
                    <el-option label="每周" value="weekly" />
                    <el-option label="3次以上/周" value="3+weekly" />
                    <el-option label="每天" value="daily" />
                  </el-select>
                </el-form-item>

                <el-form-item label="饮食习惯" prop="diet">
                  <el-input v-model="display.user_lifestyle.diet" placeholder="如：清淡/健身餐/素食/无特别偏好" />
                </el-form-item>

                <el-form-item label="宠物观" prop="pet_view">
                  <el-select v-model="display.user_lifestyle.pet_view" placeholder="请选择" clearable>
                    <el-option label="喜爱" value="love" />
                    <el-option label="都OK" value="ok" />
                    <el-option label="过敏" value="allergic" />
                    <el-option label="拒绝" value="reject" />
                  </el-select>
                </el-form-item>

                <el-form-item label="消费观" prop="spending_view">
                  <el-select v-model="display.user_lifestyle.spending_view" placeholder="请选择" clearable>
                    <el-option label="节制理性" value="frugal" />
                    <el-option label="均衡适度" value="balanced" />
                    <el-option label="享受当下" value="luxury" />
                  </el-select>
                </el-form-item>

                <el-form-item label="储蓄观" prop="saving_view">
                  <el-select v-model="display.user_lifestyle.saving_view" placeholder="请选择" clearable>
                    <el-option label="积极储蓄" value="aggressive" />
                    <el-option label="收入持平" value="balanced" />
                    <el-option label="适度储蓄" value="conservative" />
                  </el-select>
                </el-form-item>

                <el-form-item label="旅行偏好" prop="travel_pref">
                  <el-select
                    v-model="travelList"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="可多选/自定义"
                  >
                    <el-option v-for="opt in TRAVEL_OPTIONS" :key="opt" :label="opt" :value="opt" />
                  </el-select>
                  <div class="hint">保存时将转换为数组（或 JSON 字符串，见下方规范化）</div>
                </el-form-item>

                <el-form-item label="兴趣标签" prop="interests">
                  <el-select
                    v-model="interestList"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="可多选/自定义"
                  >
                    <el-option v-for="opt in INTEREST_OPTIONS" :key="opt" :label="opt" :value="opt" />
                  </el-select>
                </el-form-item>

                <el-form-item label="性格" prop="personality">
                  <el-input v-model="display.user_lifestyle.personality" placeholder="如：外向/内向/INFJ 等" />
                </el-form-item>
              </div>
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

        <!-- 6. 相册（UserMedia） -->
        <el-collapse-item title="相册" name="6">
          <template v-if="medias.length">
            <div class="media-grid">
              <el-image
                v-for="m in medias"
                :key="m.id || m.url"
                :src="m.thumb_url || m.url"
                :preview-src-list="[m.url]"
                fit="cover"
                class="media-item"
              >
                <template #error>
                  <div class="image-slot">加载失败</div>
                </template>
              </el-image>
            </div>
          </template>
          <el-empty v-else description="暂无相册" />
        </el-collapse-item>

        <!-- 7. 认证与安全（UserVerification + RiskAssessment） -->
        <el-collapse-item title="认证与安全" name="7">
          <template v-if="hasVerifyOrRisk">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="认证状态">
                {{ verifyStatusText(verification.status) }}
              </el-descriptions-item>
              <el-descriptions-item label="认证备注">
                {{ verification.reason || '—' }}
              </el-descriptions-item>
              <el-descriptions-item label="风控得分">
                {{ risk.score ?? '—' }}
              </el-descriptions-item>
              <el-descriptions-item label="风控动作">
                {{ riskActionText(risk.action) }}
              </el-descriptions-item>
              <el-descriptions-item label="风控到期">
                {{ fmtTs(risk.expire_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="暂无认证/风控信息" />
        </el-collapse-item>
      </el-collapse>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Setting, ChatLineSquare } from '@element-plus/icons-vue'
import { getDisplay, updateProfile } from '@/api'
import axios from 'axios'
import { useChatUnreadBadge } from '@/composables/useChatUnreadBadge'

/** 路由 & UID */
const router = useRouter()
const params = new URLSearchParams(location.search)
const routeUid = Number(params.get('uid') || 0)
const storedUid = Number(sessionStorage.getItem('uid') || 0)
const uid = routeUid || storedUid

if (!uid) {
  ElMessage.error('未登录，请先登录')
  router.push('/login')
} else {
  sessionStorage.setItem('uid', String(uid))
}

/** 左侧菜单选中 */
const defaultActive = ref('display')

const onSelect = (key) => {
  if (key === 'display') {
    router.push('/main')
  } else if (key === 'match') {
    router.push('/match')
  } else if (key === 'chat') {
    // 新的聊天列表页
    router.push('/chat-list')
  }
}

/** 聊天未读数（全局 store） */
const { totalUnread, totalUnreadDisplay, syncFromStorage } = useChatUnreadBadge()

function loadTotalUnread() {
  if (!uid) return
  syncFromStorage(uid)
}

/** 页面状态 */
const display = reactive({
  user_account: {},
  user_profile_public: {},
  user_intention: {},
  user_lifestyle: {},
  user_qna: [],
  media_count: 0,
  qna_count: 0,
  plan_code: '',
  user_medias: [],
  verification: {},
  risk: {}
})
const editMode = ref(false)
const saving = ref(false)
const activeNames = ref(['1', '2', '3', '4', '5', '6', '7'])

/** 顶部：完善度/会员 */
const completion = computed(() => Number(display.user_profile_public?.completion_score || 0))
const completionStatus = computed(() => {
  const p = completion.value
  if (p >= 80) return 'success'
  if (p >= 50) return 'active'
  if (p >= 30) return 'warning'
  return 'exception'
})
const vipTagType = computed(() => display.plan_code === 'vip_plus' ? 'danger' : display.plan_code === 'vip' ? 'warning' : 'info')

/** Q&A */
const questionTemplates = ['你理想的约会方式？', '你最喜欢的电影类型？', '你最喜欢的旅行目的地？', '三年内的计划？']
const selectedTemplate = ref('')
const editableQna = ref([])

function removeQna(index) {
  editableQna.value.splice(index, 1)
}

function addQnaFromTemplate() {
  if (!selectedTemplate.value) return ElMessage.warning('请选择一个问题')
  if (editableQna.value.some(q => q.question === selectedTemplate.value)) {
    return ElMessage.warning('该问题已存在')
  }
  editableQna.value.push({ question: selectedTemplate.value, answer: '' })
  selectedTemplate.value = ''
}

/** 载入数据 */
async function load() {
  try {
    const res = await getDisplay(uid)
    if (res && res.data) {
      Object.assign(display, {
        ...res.data,
        user_medias: res.data.user_medias || [],
        verification: res.data.verification || {},
        risk: res.data.risk || {}
      })
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

/** 保存相关工具 */
function formatElFormError(err) {
  // Element Plus 校验失败时，err 通常是一个 { fieldName: [{ message, field, ... }], ... } 的对象
  try {
    const fields = Object.keys(err || {})
    if (!fields.length) return '表单校验未通过'
    const firstField = fields[0]
    const firstMsg = err[firstField]?.[0]?.message || '表单校验未通过'
    return firstMsg
  } catch {
    return '表单校验未通过'
  }
}

async function validateAll() {
  try {
    await accountFormRef.value?.validate()
  } catch (e) {
    throw new Error(`基础信息：${formatElFormError(e)}`)
  }
  try {
    await intentionFormRef.value?.validate()
  } catch (e) {
    throw new Error(`择偶意向：${formatElFormError(e)}`)
  }
  try {
    await lifestyleFormRef.value?.validate()
  } catch (e) {
    throw new Error(`生活方式：${formatElFormError(e)}`)
  }
}

async function save() {
  try {
    saving.value = true

    // 1) 跑三段表单校验
    await validateAll()

    // 2) 组装 & 规范化（保持嵌套结构）
    const raw = {
      user_account:        display.user_account,
      user_profile_public: display.user_profile_public,
      user_intention:      display.user_intention,
      user_lifestyle:      display.user_lifestyle,
      user_qna:            editableQna.value.filter(q => q.answer && q.answer.trim() !== '')
    }
    normalizeIntentionForSave(raw)
    normalizeLifestyleForSave(raw)

    // 深拷贝去掉 Proxy
    const payload = JSON.parse(JSON.stringify(raw))

    // 日期字段裁剪为 YYYY-MM-DD，避免后端 DATE 列报错
    if (payload?.user_account?.birth_date) {
      payload.user_account.birth_date = String(payload.user_account.birth_date).slice(0, 10)
    }

    // 3) 发请求
    const res = await updateProfile(uid, payload)
    console.log('✅ 更新成功:', res?.data)
    ElMessage.success('资料已更新并重算完善度')
    editMode.value = false
    await load()
  } catch (e) {
    // A. axios 错误
    if (axios.isAxiosError?.(e)) {
      const status = e?.response?.status
      const data   = e?.response?.data
      const msg    = data?.detail || data?.message || e?.message || '请求失败'
      console.error('❌ 请求失败:', { status, data, msg, url: e?.config?.url, method: e?.config?.method })
      ElMessage.error(`更新失败：${msg}${status ? `（HTTP ${status}）` : ''}`)
      return
    }
    // B. 其它错误（大概率是表单校验对象 or Error）
    const msg = e?.message || formatElFormError(e) || '保存失败'
    console.error('❌ 本地校验失败:', e)
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

/** 基础信息：校验与工具 */
const PHONE_RE = /^[0-9+\s-]{6,20}$/  // 数字 / + / 空格 / -，长度 6~20

const accountFormRef = ref()
const accountRules = {
  nickname: [{ required: true, message: '请填写昵称', trigger: 'blur' }],
  phone: [
    { required: true, message: '请填写手机号', trigger: 'blur' },
    {
      validator: (_r, v, cb) => {
        if (!v) return cb()
        if (PHONE_RE.test(String(v))) {
          cb()
        } else {
          cb(new Error('手机号格式不正确'))
        }
      },
      trigger: 'blur'
    }
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  height_cm: [{
    validator: (_r, v, cb) => {
      if (v == null || v === '') return cb()
      const n = Number(v)
      if (Number.isNaN(n)) return cb(new Error('请输入数字'))
      if (n < 120 || n > 230) return cb(new Error('身高范围 120~230 cm'))
      cb()
    },
    trigger: 'change'
  }],
  weight_kg: [{
    validator: (_r, v, cb) => {
      if (v == null || v === '') return cb()
      const n = Number(v)
      if (Number.isNaN(n)) return cb(new Error('请输入数字'))
      if (n < 35 || n > 150) return cb(new Error('体重范围 35~150 kg'))
      cb()
    },
    trigger: 'change'
  }],
  avatar_url: [{
    validator: (_r, v, cb) => {
      if (!v) return cb()
      try {
        const u = new URL(String(v))
        if (!/^https?:$/.test(u.protocol)) throw new Error()
        cb()
      } catch {
        cb(new Error('请输入以 http/https 开头的URL'))
      }
    },
    trigger: 'blur'
  }]
}


function maskPhone(p) {
  if (!p) return '—'
  const s = String(p).replace(/\s+/g, '')
  if (s.length < 7) return s
  return s.slice(0, 3) + '****' + s.slice(-4)
}
function maskEmail(e) {
  if (!e) return '—'
  const s = String(e)
  const [n, h] = s.split('@')
  if (!h) return s
  const m = n.length <= 2 ? n[0] + '*' : n[0] + '***' + n.slice(-1)
  return `${m}@${h}`
}
function calcAge(birth) {
  if (!birth) return null
  try {
    const d = new Date(birth)
    if (isNaN(d.getTime())) return null
    const t = new Date()
    let age = t.getFullYear() - d.getFullYear()
    const md = (t.getMonth() + 1) * 100 + t.getDate()
    const bd = (d.getMonth() + 1) * 100 + d.getDate()
    if (md < bd) age -= 1
    return age >= 0 ? age : null
  } catch {
    return null
  }
}
function yn(v) {
  if (v === true || v === 1 || v === '1' || v === 'true') return '是'
  if (v === false || v === 0 || v === '0' || v === 'false') return '否'
  return '—'
}
function numOrDash(v) {
  return (v === 0 || v) ? v : '—'
}
function displayCities(v) {
  if (!v) return '—'
  try {
    const arr = typeof v === 'string' ? JSON.parse(v) : v
    if (Array.isArray(arr)) return arr.join('、')
  } catch {}
  return String(v)
}

/** 择偶意向：表单/城市输入/规则/映射/规范化 */
const intentionFormRef = ref()
const citiesInput = ref('')

watch(
  () => display.user_intention?.preferred_cities,
  (v) => {
    try {
      if (Array.isArray(v)) {
        citiesInput.value = v.join(', ')
      } else if (typeof v === 'string') {
        const maybe = JSON.parse(v)
        citiesInput.value = Array.isArray(maybe) ? maybe.join(', ') : v
      } else {
        citiesInput.value = ''
      }
    } catch {
      citiesInput.value = String(v || '')
    }
  },
  { immediate: true }
)

const intentionRules = {
  relationship_goal: [{ required: true, message: '请选择感情目标', trigger: 'change' }],
  age_range: [{
    validator: (_r, _v, cb) => {
      const a = Number(display.user_intention?.preferred_age_min)
      const b = Number(display.user_intention?.preferred_age_max)
      if (!Number.isFinite(a) || !Number.isFinite(b)) return cb(new Error('请填写年龄上下限'))
      if (a < 18 || b < 18) return cb(new Error('年龄不得小于18'))
      if (a > b) return cb(new Error('年龄下限不得大于上限'))
      cb()
    },
    trigger: 'change'
  }],
  height_range: [{
    validator: (_r, _v, cb) => {
      const a = display.user_intention?.preferred_height_min
      const b = display.user_intention?.preferred_height_max
      if (a == null && b == null) return cb()
      const na = Number(a)
      const nb = Number(b)
      if (!Number.isFinite(na) || !Number.isFinite(nb)) return cb(new Error('身高需为数字'))
      if (na < 140 || na > 220 || nb < 140 || nb > 220) return cb(new Error('身高范围 140~220cm'))
      if (na > nb) return cb(new Error('身高下限不得大于上限'))
      cb()
    },
    trigger: 'change'
  }],
  preferred_cities: [{
    validator: (_r, _v, cb) => {
      if (!citiesInput.value) return cb()
      const arr = citiesInput.value.split(/[，,]/).map(s => s.trim()).filter(Boolean)
      if (!arr.length) return cb(new Error('请正确填写城市或留空'))
      cb()
    },
    trigger: 'blur'
  }]
}

function goalText(v) {
  const map = { dating: '恋爱', marriage: '结婚', unsure: '未定/开放' }
  return map[String(v)] || v || '—'
}
function timelineText(v) {
  const map = { '1y': '1年内', '2y': '2年内', flexible: '随时', unknown: '暂不考虑' }
  return map[String(v)] || v || '—'
}
function childPlanText(v) {
  const map = { want: '尽快', flexible: '合适再说', dont_want: '不考虑', unknown: '暂不考虑' }
  return map[String(v)] || v || '—'
}
function familyViewText(v) {
  const map = { independent: '自己住', with_parents: '和父母住', flexible: '随意' }
  return map[String(v)] || v || '—'
}

function normalizeIntentionForSave(payload) {
  if (!payload.user_intention) payload.user_intention = {}
  const arr = (citiesInput.value || '').split(/[，,]/).map(s => s.trim()).filter(Boolean)
  // TEXT 字段保存 JSON 字符串（若后端是 JSON 数组列，把下面改成数组）
  payload.user_intention.preferred_cities = JSON.stringify(arr)
  ;['accept_long_distance', 'accept_divorce', 'accept_children'].forEach(k => {
    const v = payload.user_intention[k]
    if (v === '1' || v === 1 || v === 'true') payload.user_intention[k] = true
    else if (v === '0' || v === 0 || v === 'false') payload.user_intention[k] = false
  })
}

/** 相册/认证/风控（只读） */
const medias = computed(() => Array.isArray(display.user_medias) ? display.user_medias : [])
const verification = computed(() => display.verification || {})
const risk = computed(() => display.risk || {})
const hasVerifyOrRisk = computed(() =>
  (verification.value && verification.value.status !== undefined) ||
  (risk.value && (risk.value.score !== undefined || risk.value.action !== undefined))
)

function verifyStatusText(s) {
  const map = { 0: '待审', 1: '通过', 2: '拒绝', 3: '复审中' }
  if (s == null || s === '') return '—'
  const k = Number(s)
  return (k in map) ? map[k] : String(s)
}
function riskActionText(a) {
  const map = { 0: '无', 1: '限流', 2: '限聊', 3: '封禁' }
  if (a == null || a === '') return '—'
  const k = Number(a)
  return (k in map) ? map[k] : String(a)
}
function fmtTs(s) {
  if (!s) return '—'
  try {
    const t = String(s)
    return t.length > 19 ? t.slice(0, 19).replace('T', ' ') : t.replace('T', ' ')
  } catch {
    return String(s)
  }
}

/** 生活方式：规则/列表/watch/映射/规范化 */
const lifestyleFormRef = ref()
const lifestyleRules = {
  schedule: [{ required: false }],
  drinking: [{ required: false }],
  smoking: [{ required: false }],
  workout_freq: [{ required: false }],
  diet: [{ required: false }],
  pet_view: [{ required: false }],
  spending_view: [{ required: false }],
  saving_view: [{ required: false }],
  travel_pref: [{ required: false }],
  interests: [{ required: false }],
  personality: [{ required: false }]
}
const TRAVEL_OPTIONS = ['海岛', '徒步', '自驾', '城市漫游', '美食', '露营', '滑雪', '潜水']
const INTEREST_OPTIONS = ['电影', '音乐', '读书', '摄影', '运动', '宠物', '桌游', '舞蹈', '游戏', '二次元']
const travelList = ref([])
const interestList = ref([])

watch(
  () => display.user_lifestyle,
  (v) => {
    try {
      const src = v?.travel_pref
      travelList.value = Array.isArray(src)
        ? src
        : (typeof src === 'string' && JSON.parse(src)) || []
    } catch {
      travelList.value = []
    }
    try {
      const src2 = v?.interests
      interestList.value = Array.isArray(src2)
        ? src2
        : (typeof src2 === 'string' && JSON.parse(src2)) || []
    } catch {
      interestList.value = []
    }
  },
  { immediate: true, deep: true }
)

function scheduleText(v) {
  const m = { early: '早睡早起', normal: '正常作息', late: '晚睡晚起' }
  return m[String(v)] || v || '—'
}
function drinkingText(v) {
  const m = { never: '从不', occasionally: '偶尔', often: '经常' }
  return m[String(v)] || v || '—'
}
function smokingText(v) {
  const m = { never: '从不', occasionally: '偶尔', often: '经常' }
  return m[String(v)] || v || '—'
}
function workoutText(v) {
  const m = { none: '无', weekly: '每周', '3+weekly': '3次以上/周', daily: '每天' }
  return m[String(v)] || v || '—'
}
function petText(v) {
  const m = { love: '喜爱', ok: '都OK', allergic: '过敏', reject: '拒绝' }
  return m[String(v)] || v || '—'
}
function spendingText(v) {
  const m = { frugal: '节制理性', balanced: '均衡适度', luxury: '享受当下' }
  return m[String(v)] || v || '—'
}
function savingText(v) {
  const m = { aggressive: '积极储蓄', balanced: '收入持平', conservative: '适度储蓄' }
  return m[String(v)] || v || '—'
}
function listOrDash(v) {
  if (!v && v !== 0) return '—'
  try {
    if (Array.isArray(v)) return v.join('、')
    const may = JSON.parse(v)
    if (Array.isArray(may)) return may.join('、')
  } catch {}
  return String(v)
}

function normalizeLifestyleForSave(payload) {
  if (!payload.user_lifestyle) payload.user_lifestyle = {}
  // TEXT 字段保存 JSON 字符串（若后端是 JSON 数组列，改为数组）
  payload.user_lifestyle.travel_pref = JSON.stringify(travelList.value || [])
  payload.user_lifestyle.interests   = JSON.stringify(interestList.value || [])
  ;['diet', 'personality'].forEach(k => {
    if (payload.user_lifestyle[k] !== undefined && payload.user_lifestyle[k] !== null) {
      const s = String(payload.user_lifestyle[k]).trim()
      if (s === '') payload.user_lifestyle[k] = null
    }
  })
}

onMounted(() => {
  load()
  loadTotalUnread()
})
</script>

<style scoped>
.layout { display:flex; height:100vh; background:#f8fafc; }
.sidebar { width:264px; padding:14px; background:linear-gradient(180deg,#f8fafc,#ffffff); border-right:1px solid #eef2f7; }
.content { flex:1; padding:24px; overflow:auto; }

.sidebar-card { border-radius:18px; padding:14px; background:rgba(255,255,255,.8); backdrop-filter:saturate(160%) blur(8px); box-shadow:0 12px 30px rgba(15,23,42,.06); }
.brand { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.brand-title { font-weight:600; color:#1f2937; }
.brand-sub { color:#6b7280; font-size:12px; }
.pretty-menu { border-right:0 !important; background:transparent !important; --menu-item-radius:12px; }
:deep(.el-menu-item){ height:44px; line-height:44px; margin:6px 0; border-radius:var(--menu-item-radius); font-weight:500; color:#4b5563; transition:all .2s; }
:deep(.el-menu-item:hover){ background:#f1f5f9; }
:deep(.el-menu-item.is-active){ background:#eef2ff; color:#111827; }

.topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; }
.topbar-left { display:flex; align-items:center; gap:14px; }
.topbar-title { font-weight:600; margin-right:6px; }
.vip-line { margin-top:6px; }

.pub-item { margin-bottom:6px; }
.pub-bio { padding:8px 10px; border-radius:8px; background:#f9fafb; }

.qna-item { margin-bottom:12px; padding:8px 10px; background:#f9fafb; border-radius:8px; }
.el-divider { margin:10px 0; color:#9ca3af; }

/* 表单两列 */
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px 16px; }
.form-grid .el-form-item { margin-bottom:12px; }

/* 头像输入行 */
.avatar-row .avatar-input { display:flex; align-items:center; }

/* 提示/间距小工具 */
.hint { color:#9ca3af; font-size:12px; margin-top:4px; }
.inline-range { display:flex; align-items:center; }
.mx-6 { margin:0 6px; }

/* 相册展示 */
.media-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(120px, 1fr)); gap:10px; }
.media-item { width:100%; height:120px; border-radius:10px; overflow:hidden; background:#f3f4f6; }
.image-slot { width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#9ca3af; font-size:12px; }

/* 聊天菜单红点 */
.menu-chat-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.menu-unread-pill {
  display: inline-flex;
  min-width: 18px;
  padding: 0 5px;
  height: 18px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  justify-content: center;
  align-items: center;
}
</style>
