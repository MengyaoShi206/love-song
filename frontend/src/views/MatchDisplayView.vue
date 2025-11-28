<!-- haozong/hunlian/master/frontend/src/views/MatchDisplayView.vue -->
<template>
  <div class="layout">
    <!-- 左侧菜单 -->
    <aside class="sidebar">
      <el-card class="sidebar-card" shadow="never">
        <div class="brand">
          <div class="brand-meta">
            <div class="brand-title">匹配中心</div>
            <div class="brand-sub">发现更合适的 TA</div>
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
    <main class="content" ref="contentRef">
      <!-- 顶部：筛选 Tabs -->
      <div class="topbar">
        <el-tabs v-model="activeTab" @tab-click="onTabClick" class="tabs">
          <el-tab-pane label="为您推荐" name="recommend"></el-tab-pane>
          <el-tab-pane label="喜欢你的人" name="likedMe"></el-tab-pane>
          <el-tab-pane label="您的喜欢" name="likes"></el-tab-pane>
          <el-tab-pane label="自定义匹配" name="custom"></el-tab-pane>
          <el-tab-pane label="已双向匹配" name="mutual"></el-tab-pane>
          <el-tab-pane label="其他" name="others"></el-tab-pane>
        </el-tabs>
      </div>

      <!-- 为您推荐 -->
      <div v-if="activeTab === 'recommend'">
        <div class="toolbar">
          <el-select
            v-model="recommend.params.limit"
            size="small"
            style="width:100px"
            @change="() => { recommend.page = 1; loadRecommend() }"
          >
            <el-option :value="20" label="20条/页" />
            <el-option :value="40" label="40条/页" />
            <el-option :value="100" label="100条/页" />
          </el-select>
          <el-button size="small" @click="loadRecommend" :loading="recommend.loading">刷新推荐</el-button>
          <div class="hint">完善资料、上传清晰照片、通过认证可显著提升推荐质量</div>
        </div>

        <el-skeleton :loading="recommend.loading" animated :count="3">
          <template #template>
            <el-skeleton-item variant="image" style="width:100%;height:180px;border-radius:12px" />
            <div style="padding:10px 0">
              <el-skeleton-item variant="p" />
              <el-skeleton-item variant="text" />
            </div>
          </template>

          <template #default>
            <el-row :gutter="16">
              <el-col :span="6" v-for="u in recommend.items" :key="u.id">
                <el-card shadow="hover" class="rec-card">
                  <div class="rec-cover">
                    <img :src="u.avatar_url || placeholder" alt="profile cover" loading="lazy" />
                    <div class="rec-score">综合 {{ toPct(u?.score ?? 0) }}%</div>
                  </div>

                  <div class="rec-body">
                    <div class="rec-head">
                      <div class="left">
                        <div class="name">{{ u.nickname || ('ID'+u.id) }}</div>
                        <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                      </div>
                      <div class="right">
                        <el-button size="small" @click="goDisplay_recommend(u.id)">查看资料</el-button>

                        <!-- 喜欢按钮 / 状态 -->
                        <el-button
                          v-if="!u._liked && u.match_status !== 'matched'"
                          size="small"
                          type="danger"
                          plain
                          @click="onLike(u.id, 'recommend')"
                        >❤️ 喜欢</el-button>

                        <el-tag v-else-if="u.match_status !== 'matched'" type="warning">已喜欢</el-tag>
                        <el-tag v-else type="success">已匹配</el-tag>
                      </div>
                    </div>

                    <div class="tagline" v-if="u.tagline || u.bio">{{ u.tagline || u.bio }}</div>

                    <div class="signals">
                      <div class="sig">
                        <span>相似</span>
                        <el-progress :percentage="toPct(u.signals?.similarity)" :show-text="false" />
                      </div>
                      <div class="sig">
                        <span>互补</span>
                        <el-progress :percentage="toPct(u.signals?.complementarity)" :show-text="false" />
                      </div>
                      <div class="sig">
                        <span>意向</span>
                        <el-progress :percentage="toPct(u.signals?.intention_fit)" :show-text="false" />
                      </div>
                      <div class="sig">
                        <span>生活</span>
                        <el-progress :percentage="toPct(u.signals?.lifestyle)" :show-text="false" />
                      </div>
                      <div class="sig">
                        <span>可信</span>
                        <el-progress :percentage="toPct(u.signals?.trust_safety)" :show-text="false" />
                      </div>
                    </div>

                    <div class="reasons" v-if="u.reasons?.length">
                      <el-tag v-for="(r, idx) in u.reasons" :key="idx" size="small" effect="plain" class="mr8">
                        {{ r }}
                      </el-tag>
                    </div>
                    <div class="reason-summary" v-else>
                      {{ u.reason_summary || '多维度匹配度较高' }}
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <div v-if="!recommend.items.length" class="empty-line">
              <el-empty description="暂无推荐；建议补充资料、增加媒体并开启认证" />
            </div>

            <div class="pager" v-if="recommend.items.length">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="recommend.total"
                :page-size="recommend.params.limit"
                :current-page="recommend.page"
                @current-change="(p)=>{ recommend.page = p; loadRecommend() }"
              />
            </div>
          </template>
        </el-skeleton>
      </div>

      <!-- 您的喜欢 -->
      <div v-else-if="activeTab === 'likes'">
        <el-skeleton :loading="likes.loading" animated :count="3">
          <template #template>
            <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
            <div style="padding:8px 0">
              <el-skeleton-item variant="p" />
              <el-skeleton-item variant="text" />
            </div>
          </template>
          <template #default>
            <el-row :gutter="16">
              <el-col :span="6" v-for="u in likes.items" :key="u.id">
                <el-card shadow="hover" class="user-card">
                  <div class="user-card-head">
                    <el-avatar :size="56" :src="u.avatar_url || ''" />
                    <div class="meta">
                      <div class="name">{{ u.nickname || u.username }}</div>
                      <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                    </div>
                  </div>
                  <div class="tagline">{{ u.tagline || '—' }}</div>
                  <div class="actions">
                    <el-button size="small" @click="goDisplay(u.id)">查看资料</el-button>
                    <el-tag v-if="u.match_status==='matched'" type="success">已匹配</el-tag>
                    <el-tag v-else type="warning">等待回应</el-tag>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <div v-if="!likes.items.length" class="empty-line">
              <el-empty description="暂无喜欢的人" />
            </div>
            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="likes.total"
                :page-size="likes.page_size"
                :current-page="likes.page"
                @current-change="(p)=>{ likes.page=p; loadLikes() }"
              />
            </div>
          </template>
        </el-skeleton>
      </div>

      <!-- 喜欢您的人 -->
      <div v-else-if="activeTab === 'likedMe'">
        <el-skeleton :loading="likedMe.loading" animated :count="3">
          <template #template>
            <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
            <div style="padding:8px 0">
              <el-skeleton-item variant="p" />
              <el-skeleton-item variant="text" />
            </div>
          </template>
          <template #default>
            <el-row :gutter="16">
              <el-col :span="6" v-for="u in likedMe.items" :key="u.id">
                <el-card shadow="hover" class="user-card">
                  <div class="user-card-head">
                    <el-avatar :size="56" :src="u.avatar_url || ''" />
                    <div class="meta">
                      <div class="name">{{ u.nickname || u.username }}</div>
                      <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                    </div>
                  </div>
                  <div class="tagline">{{ u.tagline || '—' }}</div>
                  <div class="actions">
                    <el-button size="small" @click="goDisplay_likedMe(u.id)">查看资料</el-button>

                    <el-button
                      v-if="u.match_status==='waiting'"
                      size="small"
                      type="danger"
                      plain
                      @click="onLike(u.id, 'likedMe')"
                    >❤️ 喜欢回去</el-button>

                    <el-tag v-else-if="u.match_status==='pending'" type="warning">已喜欢</el-tag>
                    <el-tag v-else-if="u.match_status==='matched'" type="success">已匹配</el-tag>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <div v-if="!likedMe.items.length" class="empty-line">
              <el-empty description="暂无喜欢你的人" />
            </div>
            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="likedMe.total"
                :page-size="likedMe.page_size"
                :current-page="likedMe.page"
                @current-change="(p)=>{ likedMe.page=p; loadLikedMe() }"
              />
            </div>
          </template>
        </el-skeleton>
      </div>

      <!-- 已双向匹配 -->
      <div v-else-if="activeTab === 'mutual'">
        <el-skeleton :loading="mutual.loading" animated :count="3">
          <template #template>
            <el-skeleton-item variant="image" style="width:100%;height:140px;border-radius:12px" />
            <div style="padding:8px 0">
              <el-skeleton-item variant="p" />
              <el-skeleton-item variant="text" />
            </div>
          </template>
          <template #default>
            <el-row :gutter="16">
              <el-col :span="6" v-for="u in mutual.items" :key="u.id">
                <el-card shadow="hover" class="user-card">
                  <div class="user-card-head">
                    <el-avatar :size="56" :src="u.avatar_url || ''" />
                    <div class="meta">
                      <div class="name">{{ u.nickname || u.username }}</div>
                      <div class="sub">{{ [u.age && (u.age + '岁'), u.city].filter(Boolean).join(' · ') }}</div>
                    </div>
                  </div>
                  <div class="tagline">{{ u.tagline || '—' }}</div>
                  <div class="actions">
                    <el-button size="small" type="primary" @click="onStartChat(u.id)">发起聊天</el-button>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <div v-if="!mutual.items.length" class="empty-line">
              <el-empty description="暂无双向匹配" />
            </div>
            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="mutual.total"
                :page-size="mutual.page_size"
                :current-page="mutual.page"
                @current-change="(p)=>{ mutual.page=p; loadMutual() }"
              />
            </div>
          </template>
        </el-skeleton>
      </div>

      <!-- 自定义匹配：上面筛选 + 中间“已喜欢大卡” + 下面“未喜欢大卡” -->
      <div v-else-if="activeTab === 'custom'">
        <!-- 顶部固定筛选条 -->
        <div class="sticky-bar">
          <el-form :inline="true" label-width="auto" class="filter-form" @submit.prevent>
            <el-form-item label="性别">
              <el-select v-model="manual.form.gender" placeholder="不限" clearable style="width: 120px">
                <el-option label="男 male" value="male" />
                <el-option label="女 female" value="female" />
              </el-select>
            </el-form-item>

            <el-form-item label="年龄">
              <el-input-number v-model="manual.form.age_min" :min="16" :max="80" placeholder="最小" />
              <span class="sep">—</span>
              <el-input-number v-model="manual.form.age_max" :min="16" :max="80" placeholder="最大" />
            </el-form-item>

            <el-form-item label="身高(cm)">
              <el-input-number v-model="manual.form.height_min" :min="120" :max="230" />
              <span class="sep">—</span>
              <el-input-number v-model="manual.form.height_max" :min="120" :max="230" />
            </el-form-item>

            <el-form-item label="体重(kg)">
              <el-input-number v-model="manual.form.weight_min" :min="30" :max="200" />
              <span class="sep">—</span>
              <el-input-number v-model="manual.form.weight_max" :min="30" :max="200" />
            </el-form-item>

            <el-form-item label="城市">
              <el-input v-model="manual.form.city" placeholder="留空不限" />
            </el-form-item>

            <el-form-item label="家乡">
              <el-input v-model="manual.form.hometown" placeholder="留空不限" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="onSearchCustom">查询</el-button>
              <el-button @click="onResetCustom">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 中间 + 下方结果区域 -->
        <div class="result-area" v-loading="manual.loading">
          <template v-if="manual.items.length">
            <!-- 中间：已喜欢大卡 -->
            <el-card
              v-if="likedList.length"
              class="profile-one"
              shadow="always"
              style="margin-bottom: 16px;"
            >
              <template #header>
                <div class="header-row">
                  <span>已喜欢第 {{ manual.likedIdx }} 个 / 共已喜欢 {{ manual.likedTotal }} 个</span>
                </div>
              </template>

              <div class="profile-grid">
                <!-- 左侧：大图 -->
                <div class="pf-left">
                  <img :src="curLiked.avatar_url || placeholder" class="pf-avatar" alt="avatar" />
                </div>

                <!-- 右侧：关键信息 -->
                <div class="pf-right">
                  <!-- 标题行：名字 + 徽章 -->
                  <div class="pf-head">
                    <h2 class="pf-name">
                      {{ curLiked.nickname || curLiked.username || (curLiked.id && 'ID' + curLiked.id) || '—' }}
                    </h2>
                    <div class="pf-badges">
                      <el-tag size="small" v-if="curLiked.age">{{ curLiked.age }}岁</el-tag>
                      <el-tag size="small" v-if="curLiked.gender">{{ genderLabel(curLiked.gender) }}</el-tag>
                      <el-tag size="small" v-if="curLiked.mbti">{{ curLiked.mbti }}</el-tag>
                    </div>
                  </div>

                  <!-- 关键信息网格 -->
                  <div class="pf-meta-grid">
                    <div class="meta-item" v-if="curLiked.city"><span>城市</span><b>{{ curLiked.city }}</b></div>
                    <div class="meta-item" v-if="curLiked.hometown"><span>家乡</span><b>{{ curLiked.hometown }}</b></div>
                    <div class="meta-item" v-if="curLiked.height_cm"><span>身高</span><b>{{ curLiked.height_cm }} cm</b></div>
                    <div class="meta-item" v-if="curLiked.weight_kg"><span>体重</span><b>{{ curLiked.weight_kg }} kg</b></div>
                    <div class="meta-item" v-if="curLiked.education"><span>学历</span><b>{{ curLiked.education }}</b></div>
                    <div class="meta-item" v-if="curLiked.occupation"><span>职业</span><b>{{ curLiked.occupation }}</b></div>
                  </div>

                  <!-- Slogan / 自我介绍 -->
                  <p class="pf-tagline" v-if="curLiked.tagline">{{ curLiked.tagline }}</p>
                  <p class="pf-bio" v-if="curLiked.bio">{{ curLiked.bio }}</p>

                  <!-- 操作 + 翻页（无喜欢按钮） -->
                  <div class="pf-actions">
                    <div class="left">
                      <el-button
                        v-if="curLiked.id"
                        @click="goDisplayCustom(curLiked.id)"
                      >
                        查看资料
                      </el-button>
                      <el-tag
                        v-if="String(curLiked.match_status).toLowerCase() === 'matched'"
                        type="success"
                      >
                        已匹配
                      </el-tag>
                      <el-tag
                        v-else
                        type="warning"
                      >
                        已喜欢
                      </el-tag>
                    </div>
                    <div class="right">
                      <el-button @click="prevLiked" :disabled="manual.likedIdx <= 1">上一个</el-button>
                      <el-button
                        type="primary"
                        @click="nextLiked"
                        :disabled="manual.likedIdx >= manual.likedTotal"
                      >
                        下一个
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
            <el-empty
              v-else
              description="当前筛选下暂无已喜欢的人"
              style="margin-bottom: 16px;"
            />

            <!-- 下面：未喜欢大卡（保持原来格式 + 喜欢按钮） -->
            <template v-if="unlikedList.length">
              <el-card class="profile-one" shadow="always">
                <div class="profile-grid">
                  <!-- 左侧：大图 -->
                  <div class="pf-left">
                    <img :src="curUnliked.avatar_url || placeholder" class="pf-avatar" alt="avatar" />
                  </div>

                  <!-- 右侧：关键信息 -->
                  <div class="pf-right">
                    <!-- 标题行：名字 + 徽章 -->
                    <div class="pf-head">
                      <h2 class="pf-name">
                        {{ curUnliked.nickname || curUnliked.username || (curUnliked.id && 'ID' + curUnliked.id) || '—' }}
                      </h2>
                      <div class="pf-badges">
                        <el-tag size="small" v-if="curUnliked.age">{{ curUnliked.age }}岁</el-tag>
                        <el-tag size="small" v-if="curUnliked.gender">{{ genderLabel(curUnliked.gender) }}</el-tag>
                        <el-tag size="small" v-if="curUnliked.mbti">{{ curUnliked.mbti }}</el-tag>
                      </div>
                    </div>

                    <!-- 关键信息网格 -->
                    <div class="pf-meta-grid">
                      <div class="meta-item" v-if="curUnliked.city"><span>城市</span><b>{{ curUnliked.city }}</b></div>
                      <div class="meta-item" v-if="curUnliked.hometown"><span>家乡</span><b>{{ curUnliked.hometown }}</b></div>
                      <div class="meta-item" v-if="curUnliked.height_cm"><span>身高</span><b>{{ curUnliked.height_cm }} cm</b></div>
                      <div class="meta-item" v-if="curUnliked.weight_kg"><span>体重</span><b>{{ curUnliked.weight_kg }} kg</b></div>
                      <div class="meta-item" v-if="curUnliked.education"><span>学历</span><b>{{ curUnliked.education }}</b></div>
                      <div class="meta-item" v-if="curUnliked.occupation"><span>职业</span><b>{{ curUnliked.occupation }}</b></div>
                    </div>

                    <!-- Slogan / 自我介绍 -->
                    <p class="pf-tagline" v-if="curUnliked.tagline">{{ curUnliked.tagline }}</p>
                    <p class="pf-bio" v-if="curUnliked.bio">{{ curUnliked.bio }}</p>

                    <!-- 操作 + 翻页（保持原来的喜欢逻辑） -->
                    <div class="pf-actions">
                      <div class="left">
                        <el-button
                          v-if="curUnliked.id"
                          @click="goDisplayCustom(curUnliked.id)"
                        >
                          查看资料
                        </el-button>
                        <el-button
                          v-if="curUnliked.id && !curUnliked._liked && curUnliked.match_status !== 'matched'"
                          type="danger"
                          plain
                          :loading="likeLoading.value && likeLoading.value.has(curUnliked.id)"
                          @click="onLike(curUnliked.id, 'custom')"
                        >
                          ❤️ 喜欢
                        </el-button>
                        <el-tag
                          v-else-if="curUnliked.match_status !== 'matched'"
                          type="warning"
                        >
                          已喜欢
                        </el-tag>
                        <el-tag
                          v-else
                          type="success"
                        >
                          已匹配
                        </el-tag>
                      </div>
                      <div class="right">
                        <el-button @click="prevManual" :disabled="manual.page <= 1">上一个</el-button>
                        <el-button
                          type="primary"
                          @click="nextManual"
                          :disabled="manual.page >= manual.totalPages"
                        >
                          下一个
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </el-card>
            </template>
            <el-empty
              v-else
              description="当前筛选下暂无未喜欢的人"
            />
          </template>

          <el-empty v-else description="暂无符合条件的用户" />
        </div>
      </div>

      <!-- 其他 -->
      <div v-else>
        <el-empty description="更多匹配类别（待扩展）" />
      </div>

      <!-- 聊天广告门 -->
      <ForcedAdDialog
        v-model="showGate"
        :ad="chatAd"
        :seconds="requiredSeconds"
        :vip-plus="vipPlus"
        @finished="handleGateFinished"
        @see="handleGateSeeAd"
      />

      <!-- 广告弹窗（点赞用） -->
      <LikeAdDialog
        v-model="showAd"
        :ad="currentAd"
        :from="activeTab"
        @see="(ad) => goSeeAd(router, ad, activeTab)"
      />
    </main>
  </div>
</template>

<script setup>
defineOptions({ name: 'MatchDisplayView' }) // 供 KeepAlive include 使用

import {
  ref,
  reactive,
  watch,
  onMounted,
  nextTick,
  computed,
  onActivated,
  onBeforeUnmount
} from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { User, Setting, ChatLineSquare } from '@element-plus/icons-vue'
import {
  getDisplay,
  getManualMatch,
  getRecommendUsers,
  getMatchLikes,
  getMatchMutual,
  getLikedMe
} from '@/api'
import { ElMessage } from 'element-plus'
import { useLikeWithAd, goSeeAd } from '@/composables/useLikeWithAd.js'
import LikeAdDialog from '@/components/LikeAdDialog.vue'
import ForcedAdDialog from '@/components/ForcedAdDialog.vue'
import { useAdGateForChat } from '@/composables/useAdGateForChat'
import { useChatUnreadBadge } from '@/composables/useChatUnreadBadge'

const router = useRouter()
const route = useRoute()
const defaultActive = ref('match')
const activeTab = ref('recommend')

const likes = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const mutual = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })
const likedMe = reactive({ items: [], page: 1, page_size: 20, total: 0, loading: false })

const recommend = reactive({
  items: [],
  loading: false,
  params: { limit: 20, min_completion: 0 },
  page: 1,
  total: 0,
})

const placeholder = 'https://placehold.co/600x400?text=Profile'
const toPct = (x) => {
  const v = Number(x || 0)
  if (Number.isNaN(v)) return 0
  const p = Math.round(v * 100)
  return Math.max(0, Math.min(100, p))
}

const likedMap = reactive({})
const matchedMap = reactive({})
function _clearObj(obj) { for (const k of Object.keys(obj)) delete obj[k] }

const contentRef = ref(null)
const uid = Number(sessionStorage.getItem('uid') || 0)

/* ====== 聊天未读红点（全局 store） ====== */
const { totalUnread, totalUnreadDisplay, syncFromStorage } = useChatUnreadBadge()

function loadTotalUnread() {
  if (!uid) return
  syncFromStorage(uid)
}


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

function onTabClick(tab) {
  console.log('tab-click:', tab?.props?.name)
}

/* ========= 自定义匹配 ========= */
function genderLabel(g) {
  if (!g) return '未知'
  const s = String(g).toLowerCase()
  if (s === 'male') return '男'
  if (s === 'female') return '女'
  return g
}

/**
 * manual.items: 当前筛选下「候选池」（自定义匹配接口返回的所有人）
 * manual.likedItems: 当前筛选下「已喜欢」的人（从全局 likes 缓存里按条件过滤）
 * unlikedList: 当前筛选下「未喜欢」的人（用于下面那块大卡 + 点赞）
 * likedList: 当前筛选下「已喜欢」的人（用于中间那块大卡）
 */
const manual = reactive({
  items: [],       // 当前筛选下的候选池（已喜欢 + 未喜欢，来自 getManualMatch）
  likedItems: [],  // 当前筛选下的“已喜欢”池（从 likesCacheList 过滤得出）
  loading: false,
  page: 1,         // 未喜欢区当前索引（1-based）
  total: 0,        // 未喜欢总数（= unlikedList.length）
  totalPages: 1,   // 未喜欢“页数”（单卡翻页）
  likedIdx: 1,     // 已喜欢区当前索引（1-based）
  likedTotal: 0,   // 已喜欢总数（= likedList.length）
  form: {
    gender: null,
    age_min: null, age_max: null,
    height_min: null, height_max: null,
    weight_min: null, weight_max: null,
    city: '', hometown: ''
  }
})

// 全局缓存“我的喜欢”完整列表，用于自定义区中间卡
const likesCacheList = ref([])

const likedList = computed(() => manual.likedItems || [])

const unlikedList = computed(() => {
  return manual.items.filter(it => {
    const id = it.id
    const st = String(it.match_status || '').toLowerCase()
    const likedFlag = likedMap[id] || it._liked
    const isMatched = matchedMap[id] || st === 'matched' || st === 'already_matched' || st === 'accepted'
    const isPending = st === 'pending'
    return !(likedFlag || isMatched || isPending)
  })
})

const curLiked = computed(() => {
  if (!likedList.value.length) return {}
  const idx = Math.min(Math.max(manual.likedIdx || 1, 1), likedList.value.length)
  return likedList.value[idx - 1]
})

const curUnliked = computed(() => {
  if (!unlikedList.value.length) return {}
  const idx = Math.min(Math.max(manual.page || 1, 1), unlikedList.value.length)
  return unlikedList.value[idx - 1]
})

// 监听 likedList / unlikedList 自动更新计数和边界
watch(likedList, (arr) => {
  manual.likedTotal = arr.length || 0
  if (manual.likedIdx > manual.likedTotal) {
    manual.likedIdx = manual.likedTotal || 1
  }
})

watch(unlikedList, (arr) => {
  manual.total = arr.length || 0
  manual.totalPages = arr.length || 1
  if (manual.page > manual.totalPages) {
    manual.page = manual.totalPages || 1
  }
})

/** ====== 用筛选条件过滤“我的喜欢”列表，重建 manual.likedItems ====== **/
function personMatchesForm(p, f) {
  // 性别
  if (f.gender) {
    const g = String(p.gender || '').toLowerCase()
    if (g && g !== String(f.gender).toLowerCase()) return false
  }

  // 城市（简单包含匹配）
  if (f.city) {
    const c = String(p.city || '').trim()
    if (c && !c.includes(String(f.city).trim())) return false
  }

  // 家乡（如果 likes 里有的话，就按包含匹配；没有就不限制）
  if (f.hometown) {
    const h = String(p.hometown || '').trim()
    if (h && !h.includes(String(f.hometown).trim())) return false
  }

  // 年龄（如果 likes 里有 age，则按区间过滤；没有 age 就不限制）
  const age = Number(p.age)
  if (!Number.isNaN(age)) {
    if (f.age_min != null && age < f.age_min) return false
    if (f.age_max != null && age > f.age_max) return false
  }

  // 身高 / 体重：大概率 likes 接口不返回；如果返回再按区间限制
  const height = Number(p.height_cm ?? p.height)
  if (!Number.isNaN(height)) {
    if (f.height_min != null && height < f.height_min) return false
    if (f.height_max != null && height > f.height_max) return false
  }

  const weight = Number(p.weight_kg ?? p.weight)
  if (!Number.isNaN(weight)) {
    if (f.weight_min != null && weight < f.weight_min) return false
    if (f.weight_max != null && weight > f.weight_max) return false
  }

  return true
}

function rebuildManualLikedFromCache() {
  try {
    const allLikes = Array.isArray(likesCacheList.value) ? likesCacheList.value : []
    const filtered = allLikes.filter(p => personMatchesForm(p, manual.form))
    manual.likedItems = filtered
    if (!filtered.length) {
      manual.likedIdx = 1
    } else if (manual.likedIdx < 1) {
      manual.likedIdx = 1
    } else if (manual.likedIdx > filtered.length) {
      manual.likedIdx = filtered.length
    }
  } catch (e) {
    manual.likedItems = []
    manual.likedIdx = 1
  }
}

// 筛选条件变化 / likes 缓存变化时，自动重建“已喜欢池”
watch(() => manual.form, () => {
  rebuildManualLikedFromCache()
}, { deep: true })

watch(likesCacheList, () => {
  rebuildManualLikedFromCache()
})

async function loadManualDefaults() {
  try {
    const { data } = await getDisplay(uid)
    const intent = data?.user_intention || {}
    manual.form.age_min    = intent.preferred_age_min ?? null
    manual.form.age_max    = intent.preferred_age_max ?? null
    manual.form.height_min = intent.preferred_height_min ?? null
    manual.form.height_max = intent.preferred_height_max ?? null
    manual.form.weight_min = intent.preferred_weight_min ?? null
    manual.form.weight_max = intent.preferred_weight_max ?? null
  } catch (e) {}
}

// 注意：这里不再用 page 做分页，而是一次拉一批，下面“未喜欢卡片”用 manual.page 在 unlikedList 里翻页
async function fetchManual(_p = 1) {
  manual.loading = true
  try {
    const params = { ...manual.form, page: 1, page_size: 500 } // 一次拉最多 500 个
    const { data } = await getManualMatch(uid, params)
    const items = Array.isArray(data?.items) ? data.items : []
    hydrateFlags(items)
    manual.items = items

    if (!items.length) {
      manual.page = 1
    } else if (!manual.page || manual.page < 1) {
      manual.page = 1
    }

    // 每次刷新候选池后，用当前筛选 + 全局 likes 缓存重建“已喜欢池”
    rebuildManualLikedFromCache()
  } catch (e) {
    manual.items = []
    manual.page = 1
    manual.total = 0
    manual.totalPages = 1
  } finally {
    manual.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

function onSearchCustom() {
  manual.page = 1
  manual.likedIdx = 1
  fetchManual(1)
}

function onResetCustom() {
  manual.form = {
    gender: null,
    age_min: null, age_max: null,
    height_min: null, height_max: null,
    weight_min: null, weight_max: null,
    city: '', hometown: ''
  }
  manual.page = 1
  manual.likedIdx = 1
  loadManualDefaults().then(() => fetchManual(1))
}

function prevManual() {
  if (manual.page > 1) manual.page -= 1
}
function nextManual() {
  if (manual.page < manual.totalPages) manual.page += 1
}

function prevLiked() {
  if (manual.likedIdx > 1) manual.likedIdx -= 1
}
function nextLiked() {
  if (manual.likedIdx < manual.likedTotal) manual.likedIdx += 1
}

// —— 会话存储 key 助手（只作用于“自定义匹配”tab）——
const CK = (k) => `mdv.custom.${k}`

function saveCustomState(scrollEl = null) {
  try {
    sessionStorage.setItem(CK('form'), JSON.stringify(manual.form || {}))
    sessionStorage.setItem(CK('pager'), JSON.stringify({
      page: manual.page,
      likedIdx: manual.likedIdx
    }))
    sessionStorage.setItem(CK('activeTab'), String(activeTab.value || 'recommend'))
    const y = scrollEl ? (scrollEl.scrollTop ?? 0) : (contentRef.value?.scrollTop ?? 0)
    sessionStorage.setItem(CK('scrollY'), String(y))
    sessionStorage.setItem(CK('hasCache'), '1')
  } catch {}
}

let restoredOnce = false
function restoreCustomState() {
  if (restoredOnce) return false
  try {
    const has = sessionStorage.getItem(CK('hasCache')) === '1'
    if (!has) return false

    if (!route.query.tab) {
      const t = sessionStorage.getItem(CK('activeTab'))
      if (t && ['recommend','likedMe','likes','mutual','custom','others'].includes(t)) {
        activeTab.value = t
      }
    }

    const fs = sessionStorage.getItem(CK('form'))
    const pg = sessionStorage.getItem(CK('pager'))
    if (fs) Object.assign(manual.form, JSON.parse(fs))
    if (pg) {
      const { page, likedIdx } = JSON.parse(pg)
      manual.page = page || 1
      manual.likedIdx = likedIdx || 1
    }

    restoredOnce = true
    return true
  } catch {
    return false
  }
}

function restoreCustomScroll() {
  try {
    const y = Number(sessionStorage.getItem(CK('scrollY')) || 0)
    if (!Number.isNaN(y) && contentRef.value) {
      contentRef.value.scrollTo({ top: y, behavior: 'auto' })
    }
  } catch {}
}

/** =========== URL <-> 状态：从 query 初始化、构造 query =========== */
function parseNumberMaybe(v) {
  if (v === '' || v === null || v === undefined) return null
  const n = Number(v); return Number.isNaN(n) ? null : n
}
function initCustomFromQuery(q) {
  if (!q) return
  if (q.gender) manual.form.gender = String(q.gender)
  if (q.city != null) manual.form.city = String(q.city)
  if (q.hometown != null) manual.form.hometown = String(q.hometown)

  const ageMin = parseNumberMaybe(q.age_min)
  const ageMax = parseNumberMaybe(q.age_max)
  const hMin   = parseNumberMaybe(q.height_min)
  const hMax   = parseNumberMaybe(q.height_max)
  const wMin   = parseNumberMaybe(q.weight_min)
  const wMax   = parseNumberMaybe(q.weight_max)
  if (ageMin != null) manual.form.age_min = ageMin
  if (ageMax != null) manual.form.age_max = ageMax
  if (hMin   != null) manual.form.height_min = hMin
  if (hMax   != null) manual.form.height_max = hMax
  if (wMin   != null) manual.form.weight_min = wMin
  if (wMax   != null) manual.form.weight_max = wMax

  const page = parseNumberMaybe(q.page)
  const likedIdx = parseNumberMaybe(q.likedIdx)
  if (page != null) manual.page = page
  if (likedIdx != null) manual.likedIdx = likedIdx
}
function buildCustomQuery() {
  const q = { from: 'custom', me: uid }
  const f = manual.form
  if (f.gender) q.gender = f.gender
  if (f.city) q.city = f.city
  if (f.hometown) q.hometown = f.hometown
  ;[['age_min','age_max'],['height_min','height_max'],['weight_min','weight_max']].forEach(([a,b])=>{
    if (f[a] != null) q[a] = f[a]
    if (f[b] != null) q[b] = f[b]
  })
  if (manual.page != null) q.page = manual.page
  if (manual.likedIdx != null) q.likedIdx = manual.likedIdx
  return q
}

/** ============= 点赞 + 广告（统一入口） ============= */
const {
  showAd,
  currentAd,
  likeThenMaybeAd,
  closeAd,
} = useLikeWithAd({
  limit: 1000,
  enforceAd: true,
  autoRotate: true,
  fallbackAd: { id: 1, destination: '/ad/1', title: '精选推荐' },
})

const likeLoading = ref(new Set())
const lastLikeFrom = ref('recommend')

async function onLike(targetId, from = '') {
  if (likeLoading.value.has(targetId)) return
  likeLoading.value.add(targetId)
  try {
    const { adOpened, result } = await likeThenMaybeAd(uid, targetId)

    // 刷新 likes / mutual 等列表
    await refreshByKeys(result?.refresh || [])

    const st = result?.status
    markRecommendCard(targetId, st)
    markManualCard(targetId, st)
    removeFromRecommend(targetId)

    lastLikeFrom.value = from || activeTab.value || 'recommend'

    if (adOpened && currentAd.value) {
      showAd.value = true
    } else {
      ElMessage.warning('暂时没有可展示的活动')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  } finally {
    likeLoading.value.delete(targetId)
  }
}

/* ========= 其它列表加载 ========= */
async function loadLikes() {
  try {
    likes.loading = true
    const { data } = await getMatchLikes(uid, { page: likes.page, page_size: likes.page_size })
    Object.assign(likes, data, { loading: false })
  } catch (e) {
    likes.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function loadLikedMe() {
  try {
    likedMe.loading = true
    const { data } = await getLikedMe(uid, { page: likedMe.page, page_size: likedMe.page_size, waiting_only: 0 })
    Object.assign(likedMe, data, { loading: false })
  } catch (e) {
    likedMe.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function loadMutual() {
  try {
    mutual.loading = true
    const { data } = await getMatchMutual(uid, { page: mutual.page, page_size: mutual.page_size })
    Object.assign(mutual, data, { loading: false })
  } catch (e) {
    mutual.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

async function refreshByKeys(keys = []) {
  const todo = new Set(keys)
  const tasks = []
  if (todo.has('likes')) {
    tasks.push(loadLikes())
    tasks.push(refreshLikesCache())   // 同时刷新全局 likes 缓存，确保“已喜欢区”同步
  }
  if (todo.has('likedMe')) tasks.push(loadLikedMe())
  if (todo.has('mutual'))  tasks.push(loadMutual())
  if (!tasks.length) tasks.push(refreshLikesCache())
  await Promise.all(tasks)
}

async function refreshLikesCache() {
  try {
    const { data } = await getMatchLikes(uid, { page: 1, page_size: 1000 })
    _clearObj(likedMap)
    const arr = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
    likesCacheList.value = arr
    for (const it of arr) {
      const id = extractUserId(it)
      if (!Number.isNaN(id)) likedMap[id] = true
    }
    // likes 缓存更新后，重建“已喜欢池”
    rebuildManualLikedFromCache()
  } catch(e) {}
}

async function refreshMutualCache() {
  try {
    const { data } = await getMatchMutual(uid, { page: 1, page_size: 1000 })
    _clearObj(matchedMap)
    const arr = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
    for (const it of arr) {
      const id = extractUserId(it)
      if (!Number.isNaN(id)) matchedMap[id] = true
    }
  } catch(e) {}
}

async function loadRecommend() {
  recommend.loading = true
  try {
    const { data } = await getRecommendUsers(uid, {
      limit: recommend.params.limit,
      page: recommend.page,
      min_completion: recommend.params.min_completion
    })
    const items = Array.isArray(data?.items) ? data.items : []
    items.sort((a, b) => (b?.score || 0) - (a?.score || 0))
    hydrateFlags(items)
    const total =
      Number.isFinite(Number(data?.total)) ? Number(data.total) :
      Number.isFinite(Number(data?.count)) ? Number(data.count) :
      Number.isFinite(Number(data?.total_count)) ? Number(data.total_count) :
      Number(items.length)
    recommend.items = items
    recommend.total = total
  } catch (e) {
    console.error('recommend api error:', e?.response?.status, e?.response?.data || e?.message)
    recommend.items = []
    recommend.total = 0
  } finally {
    recommend.loading = false
    await nextTick()
    scrollListToTop(false)
  }
}

function hydrateFlags(list) {
  for (const it of list) {
    if (matchedMap[it.id]) {
      it.match_status = 'matched'
      it._liked = true
    } else if (likedMap[it.id]) {
      it.match_status = it.match_status || 'pending'
      it._liked = true
    } else {
      it._liked = false
      if (!it.match_status) delete it.match_status
    }
  }
}
function markRecommendCard(targetId, status) {
  const it = recommend.items.find(x => x.id === targetId)
  if (!it) return
  it._liked = true
  const isMatched = status === 'matched' || status === 'already_matched' || status === 'accepted'
  if (isMatched) {
    it.match_status = 'matched'
    matchedMap[targetId] = true
  } else {
    it.match_status = it.match_status || 'pending'
    likedMap[targetId] = true
  }
}

// 详情页点赞后，会广播 refresh-after-like 事件，这里统一接收
function handleRefreshAfterLike(evt) {
  const detail = evt.detail || {}
  const tid = Number(detail.targetId)
  const status = detail.status
  const refresh = detail.refresh || []

  if (refresh.length) {
    refreshByKeys(refresh)
  }

  if (!Number.isNaN(tid)) {
    markRecommendCard(tid, status)
    markManualCard(tid, status)
    removeFromRecommend(tid)
  }
}

// 注册全局监听
window.addEventListener('refresh-after-like', handleRefreshAfterLike)

// 组件卸载时解绑（防止重复）
onBeforeUnmount(() => {
  window.removeEventListener('refresh-after-like', handleRefreshAfterLike)
})

function markManualCard(targetId, status) {
  const isMatched = status === 'matched' || status === 'already_matched' || status === 'accepted'

  // 在 manual.items 里同步状态（影响“未喜欢区”）
  const it = manual.items.find(x => x.id === targetId)
  if (it) {
    it._liked = true
    if (isMatched) {
      it.match_status = 'matched'
      matchedMap[targetId] = true
    } else {
      it.match_status = it.match_status || 'pending'
      likedMap[targetId] = true
    }
  }

  // 同时把这个人也同步进 likesCacheList，从而立刻出现在“已喜欢区”
  const cacheArr = Array.isArray(likesCacheList.value) ? likesCacheList.value.slice() : []
  const inCache = cacheArr.some(p => Number(p.id) === Number(targetId))
  if (!inCache) {
    cacheArr.push({
      id: targetId,
      match_status: isMatched ? 'matched' : 'pending',
      _liked: true,
      // 其它展示字段，如果 manual.items 里有就顺手带上
      avatar_url: it?.avatar_url,
      nickname: it?.nickname,
      username: it?.username,
      age: it?.age,
      city: it?.city,
      gender: it?.gender,
      tagline: it?.tagline,
      hometown: it?.hometown,
      height_cm: it?.height_cm,
      weight_kg: it?.weight_kg,
      education: it?.education,
      occupation: it?.occupation,
      mbti: it?.mbti,
      bio: it?.bio,
    })
    likesCacheList.value = cacheArr
  }

  // 更新“已喜欢池”
  rebuildManualLikedFromCache()
}

// 把某个用户从“为您推荐”列表中移除
function removeFromRecommend(targetId) {
  const id = Number(targetId)
  if (Number.isNaN(id)) return
  const before = recommend.items.length
  recommend.items = recommend.items.filter(u => u.id !== id)
  if (before > recommend.items.length && typeof recommend.total === 'number') {
    recommend.total = Math.max(0, recommend.total - 1)
  }
}

watch(activeTab, async (t) => {
  if (t === 'recommend') {
    await Promise.all([refreshLikesCache(), refreshMutualCache()])
    await loadRecommend()
  }
  if (t === 'likes')    loadLikes()
  if (t === 'mutual')   loadMutual()
  if (t === 'likedMe')  loadLikedMe()
  if (t === 'custom') {
    const restored = restoreCustomState()
    if (restored) {
      await fetchManual(manual.page || 1)
      await nextTick()
      restoreCustomScroll()
    } else {
      initCustomFromQuery(route.query)
      if (!manual.page) manual.page = 1
      await loadManualDefaults()
      await fetchManual(manual.page)
    }
  }
  await nextTick()
  scrollListToTop(false)
})

function goDisplay(id, newTab = false) {
  const resolved = router.resolve({ name: 'display', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}
function goDisplay_likedMe(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayLiked', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}
function goDisplay_recommend(id, newTab = false) {
  const resolved = router.resolve({ name: 'displayRecommend', params: { uid: id } })
  newTab ? window.open(resolved.href, '_blank') : router.push(resolved)
}

/** 进入自定义详情前，先保存状态 + 带上 query */
function goDisplayCustom(id) {
  saveCustomState(contentRef.value)
  const query = buildCustomQuery()
  router.push({ name: 'displayCustom', params: { uid: id }, query })
}

onBeforeRouteLeave((_to, _from, next) => {
  if (activeTab.value === 'custom') {
    saveCustomState(contentRef.value)
  }
  next()
})

function scrollListToTop(smooth = false) {
  const el = contentRef.value
  if (!el) return
  if ('scrollTo' in el) el.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' })
  else el.scrollTop = 0
}
function extractUserId(it) {
  const cand = [it?.id, it?.uid, it?.user_id, it?.likee_id, it?.target_id, it?.user_b, it?.user?.id, it?.profile?.user_id]
  for (const v of cand) {
    const n = Number(v)
    if (!Number.isNaN(n)) return n
  }
  return NaN
}

/* ========= 发起聊天 · 15 秒强制广告 ========= */
const {
  showGate,
  chatAd,
  requiredSeconds,
  vipPlus,
  openAdBeforeChat,
  handleGateFinished,
  handleGateSeeAd,
} = useAdGateForChat(router)

async function onStartChat(userId) {
  if (!userId) return
  try {
    // 交给 useAdGateForChat 处理：VIP 直接跳转，非 VIP 先看广告再进 /chat-list
    await openAdBeforeChat(userId)
  } catch (e) {
    console.error(e)
    ElMessage.error('暂时无法发起聊天，请稍后再试')
  }
}

/* ========= 首屏 ========= */
onMounted(async () => {
  const init = String(route.query.tab || '')
  if (['recommend','likedMe','likes','mutual','custom','others'].includes(init)) {
    activeTab.value = init
  } else {
    const last = sessionStorage.getItem(CK('activeTab'))
    if (last && ['recommend','likedMe','likes','mutual','custom','others'].includes(last)) {
      activeTab.value = last
    }
  }

  // 先把全局 likes / mutual 缓存起来，保证 hydrateFlags 有参照
  await Promise.all([refreshLikesCache(), refreshMutualCache()])

  if (activeTab.value === 'recommend')      await loadRecommend()
  else if (activeTab.value === 'likes')     await loadLikes()
  else if (activeTab.value === 'likedMe')   await loadLikedMe()
  else if (activeTab.value === 'mutual')    await loadMutual()
  else if (activeTab.value === 'custom') {
    const restored = restoreCustomState()
    if (restored) {
      await fetchManual(manual.page || 1)
      await nextTick()
      restoreCustomScroll()
    } else {
      initCustomFromQuery(route.query)
      if (!manual.page) manual.page = 1
      await loadManualDefaults()
      await fetchManual(manual.page)
    }
  }

  await nextTick()
  scrollListToTop(false)
  loadTotalUnread()
})

onActivated(() => {
  loadTotalUnread()
  if (activeTab.value === 'custom' && !restoredOnce) {
    initCustomFromQuery(route.query)
  }
})
</script>

<style scoped>
/* —— 与 MainLayout.vue 保持一致的布局与样式 —— */
.layout { display: flex; height: 100vh; background: #f8fafc; }
.sidebar { width: 264px; padding: 14px; background: linear-gradient(180deg, #f8fafc, #ffffff); border-right: 1px solid #eef2f7; }
.content { flex: 1; padding: 24px; overflow: auto; }
.sidebar-card { border-radius: 18px; padding: 14px; background: rgba(255, 255, 255, 0.8); backdrop-filter: saturate(160%) blur(8px); box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06); }
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.brand-title { font-weight: 600; color: #1f2937; }
.brand-sub { color: #6b7280; font-size: 12px; }
.pretty-menu { border-right: 0 !important; background: transparent !important; --menu-item-radius: 12px; }
:deep(.el-menu-item) { height: 44px; line-height: 44px; margin: 6px 0; border-radius: var(--menu-item-radius); font-weight: 500; color: #4b5563; transition: all .2s ease; }
:deep(.el-menu-item:hover) { background: #f1f5f9; }
:deep(.el-menu-item.is-active) { background: #eef2ff; color: #111827; }
.topbar { display: flex; align-items: center; justify-content: flex-start; margin-bottom: 16px; position: relative; z-index: 5; background: #f8fafc; }
.tabs { --el-tabs-header-height: 46px; }
.user-card { margin-bottom: 16px; border-radius: 12px; }
.user-card-head { display: flex; align-items: center; gap: 12px; }
.meta .name { font-weight: 600; }
.meta .sub { font-size: 12px; color: #6b7280; }
.tagline { margin: 10px 0; color: #374151; min-height: 20px; }
.actions { display: flex; gap: 8px; }
.pager { display: flex; justify-content: center; padding: 12px 0; }
.empty-line { padding: 24px 0; }
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.toolbar .hint { font-size: 12px; color: #6b7280; }
.rec-card { border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.rec-cover { position: relative; width: 100%; height: 180px; overflow: hidden; border-radius: 10px; }
.rec-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rec-badges { position: absolute; left: 8px; top: 8px; display: flex; gap: 6px; }
.rec-score { position: absolute; right: 8px; bottom: 8px; font-size: 12px; background: rgba(17,24,39,0.72); color: #fff; padding: 4px 8px; border-radius: 10px; }
.rec-body { padding: 10px 2px 2px; }
.rec-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.rec-head .name { font-weight: 600; }
.rec-head .sub { color: #6b7280; font-size: 12px; margin-top: 2px; }
.signals { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; margin-top: 8px; }
.sig { display: grid; grid-template-columns: 40px 1fr; align-items: center; gap: 8px; font-size: 12px; color: #6b7280; }
.reasons { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.mr8 { margin-right: 8px; }
.reason-summary { margin-top: 8px; color: #374151; font-size: 13px; }

.profile-one { width: 980px; max-width: 100%; }
.profile-grid { display: grid; grid-template-columns: 360px 1fr; gap: 18px; }
.pf-left { display: flex; align-items: flex-start; justify-content: center; }
.pf-avatar { width: 100%; max-width: 340px; aspect-ratio: 1/1; object-fit: cover; border-radius: 14px; border: 1px solid #eee; }
.pf-right { display: flex; flex-direction: column; gap: 10px; }
.pf-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.pf-name { margin: 0; font-size: 22px; font-weight: 700; }
.pf-badges { display: flex; gap: 8px; flex-wrap: wrap; }

.pf-meta-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 10px 14px; }
.meta-item { padding: 8px 10px; background: #f9fafb; border-radius: 10px; }
.meta-item span { color: #6b7280; font-size: 12px; margin-right: 6px; }
.meta-item b { color: #111827; font-weight: 600; }

.pf-tagline { margin: 6px 0 0; font-weight: 600; color: #111827; }
.pf-bio { margin: 2px 0 0; color: #4b5563; }

.pf-actions { margin-top: 8px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.pf-actions .left, .pf-actions .right { display: flex; gap: 8px; }

.sticky-bar { position: sticky; top: 0; z-index: 20; background: #fff; padding: 10px 12px; margin: -12px -12px 12px -12px; border-bottom: 1px solid #f0f0f0; }
.filter-form .sep { margin: 0 6px; color: #999; }

.result-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.header-row { display: flex; align-items: center; justify-content: space-between; font-weight: 500; }

@media (max-width: 960px) {
  .profile-grid { grid-template-columns: 1fr; }
  .pf-avatar { max-width: 100%; }
  .pf-meta-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .rec-cover { height: 160px; }
}

/* 红点*/
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
