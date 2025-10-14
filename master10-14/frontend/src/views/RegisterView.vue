<template>
  <el-card class="box-card" style="max-width: 720px; margin: 24px auto;">
    <h2>注册</h2>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" status-icon>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="3-20字符，字母数字下划线" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="昵称" prop="nickname">
            <el-input v-model="form.nickname" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="name@example.com" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="手机" prop="phone">
            <el-input v-model="form.phone" placeholder="仅数字，11位或留空" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="性别" prop="gender">
            <el-select v-model="form.gender" placeholder="请选择">
              <el-option label="male" value="male" />
              <el-option label="female" value="female" />
              <el-option label="other" value="other" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="城市" prop="city">
            <el-input v-model="form.city" placeholder="如：Beijing" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="头像URL" prop="avatar_url">
        <el-input v-model="form.avatar_url" placeholder="https://..." />
      </el-form-item>

      <el-form-item label="密码哈希" prop="password_hash">
        <el-input v-model="form.password_hash" placeholder="演示可填 hash 或你的哈希" />
      </el-form-item>

      <el-space>
        <el-button type="primary" :loading="loading" @click="onSubmit">提交注册</el-button>
        <el-button @click="onReset">重置</el-button>
      </el-space>
    </el-form>
  </el-card>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { registerUser } from '../api'

const router = useRouter()
const loading = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  gender: '',
  city: '',
  avatar_url: '',
  password_hash: 'hash'
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{3,20}$/, message: '3-20位字母/数字/下划线', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] }
  ],
  phone: [
    { validator: (_, v, cb) => {
        if (!v) return cb() 
        if (!/^\d{11}$/.test(v)) return cb(new Error('手机号需为11位数字或留空'))
        cb()
      }, trigger: 'blur'
    }
  ],
  password_hash: [
    { required: true, message: '请填写密码哈希（演示可用 "hash"）', trigger: 'blur' },
    { min: 3, message: '长度过短', trigger: 'blur' }
  ],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  city: [{ required: true, message: '请输入城市', trigger: 'blur' }],
  avatar_url: [
    { validator: (_, v, cb) => {
        if (!v) return cb()
        try { new URL(v); cb() } catch { cb(new Error('URL格式不正确')) }
      }, trigger: 'blur'
    }
  ]
}

function onReset() {
  formRef.value?.resetFields()
}

async function onSubmit() {
  try {
    await formRef.value.validate()
  } catch (e) {
    // 校验失败：会在表单项下方显示具体错误，这里再给个弹窗
    ElMessageBox.alert('请检查表单项红字错误提示并修正后再提交。', '格式校验未通过', {
      type: 'error'
    })
    return
  }

  try {
    loading.value = true
    const { data } = await registerUser(form)
    await ElMessageBox.alert('注册成功！将进入主页。', '成功', { type: 'success' })
    // 保存 uid
    localStorage.setItem('uid', String(data.id))

    // 跳转到主页
    router.push({ path: '/main', query: { uid: String(data.id) } })
  } catch (e) {
    const msg = e?.response?.data?.detail || e.message
    ElMessageBox.alert(msg, '注册失败', { type: 'error' })
  } finally {
    loading.value = false
  }
}
</script>
