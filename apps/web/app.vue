<template>
  <UiTooltipProvider :delay-duration="150">
    <NuxtLayout><NuxtPage :page-key="(route) => route.fullPath" /></NuxtLayout>
    <UiToaster position="bottom-right" close-button :duration="4500" />
  </UiTooltipProvider>
</template>
