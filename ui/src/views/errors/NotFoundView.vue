<template>
  <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-5xl px-4">
    <div class="flex items-center">
      <div class="relative w-1/2">
        <img class="w-full" src="@/assets/images/404.png" alt="404" />
        <img class="absolute w-20 left-cloud animate-cloudLeft" src="@/assets/images/404_cloud.png" alt="cloud" />
        <img class="absolute w-12 mid-cloud animate-cloudMid" src="@/assets/images/404_cloud.png" alt="cloud" />
        <img class="absolute w-16 right-cloud animate-cloudRight" src="@/assets/images/404_cloud.png" alt="cloud" />
      </div>

      <div class="w-1/2 pl-8 space-y-4">
        <div class="text-3xl font-bold text-blue-500 opacity-0 animate-slideUp">OOPS!</div>
        <div class="text-sm text-blue-400 opacity-0 animate-slideUp delay-100">
          前往
          <a
            class="text-blue-500  cursor-pointer"
            @click="goHome"
          >
            AI Agent首页
          </a>
        </div>
        <div class="text-xl font-bold text-gray-400 opacity-0 animate-slideUp delay-200">
          {{ message }}
        </div>
        <div class="text-sm text-gray-400 opacity-0 animate-slideUp delay-300">
          请检查您的地址是否正确，或者返回主页
        </div>
        <button
          class="mt-4 bg-blue-500 text-white rounded-full px-6 py-2 opacity-0 animate-slideUp delay-500"
          @click="goHome"
        >
          Back to home
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const message = '服务器无法正常提供信息，或是服务器无法回应...'

function goHome() {
  router.push('/home')
}
</script>

<style scoped>
@keyframes cloudLeft {
  0% {
    top: 17px;
    left: 220px;
    opacity: 0;
  }
  20% {
    top: 33px;
    left: 188px;
    opacity: 1;
  }
  80% {
    top: 81px;
    left: 92px;
    opacity: 1;
  }
  100% {
    top: 97px;
    left: 60px;
    opacity: 0;
  }
}

@keyframes cloudMid {
  0% {
    top: 10px;
    left: 420px;
    opacity: 0;
  }
  20% {
    top: 40px;
    left: 360px;
    opacity: 1;
  }
  70% {
    top: 130px;
    left: 180px;
    opacity: 1;
  }
  100% {
    top: 160px;
    left: 120px;
    opacity: 0;
  }
}

@keyframes cloudRight {
  0% {
    top: 100px;
    left: 500px;
    opacity: 0;
  }
  20% {
    top: 120px;
    left: 460px;
    opacity: 1;
  }
  80% {
    top: 180px;
    left: 340px;
    opacity: 1;
  }
  100% {
    top: 200px;
    left: 300px;
    opacity: 0;
  }
}

@keyframes slideUp {
  0% {
    transform: translateY(60px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

.animate-cloudLeft {
  animation: cloudLeft 2s linear forwards 1s;
}
.animate-cloudMid {
  animation: cloudMid 2s linear forwards 1.2s;
}
.animate-cloudRight {
  animation: cloudRight 2s linear forwards 1s;
}
.animate-slideUp {
  animation: slideUp 0.5s ease-out forwards;
}
.delay-100 {
  animation-delay: 0.1s;
}
.delay-200 {
  animation-delay: 0.2s;
}
.delay-300 {
  animation-delay: 0.3s;
}
.delay-500 {
  animation-delay: 0.5s;
}

/* Position clouds initially */
.left-cloud {
  top: 17px;
  left: 220px;
}
.mid-cloud {
  top: 10px;
  left: 420px;
}
.right-cloud {
  top: 100px;
  left: 500px;
}
</style>
