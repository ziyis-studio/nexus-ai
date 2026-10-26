export const useFeedback = () => {
  const feedback = useState('feedback', () => '')
  const success = (message: string) => {
    feedback.value = message
    setTimeout(() => {
      feedback.value = ''
    }, 4500)
  }
  return { feedback, success }
}
