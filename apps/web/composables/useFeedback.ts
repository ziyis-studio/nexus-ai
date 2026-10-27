import { toast } from 'vue-sonner'

export const useFeedback = () => ({ success: (message: string) => toast.success(message) })
