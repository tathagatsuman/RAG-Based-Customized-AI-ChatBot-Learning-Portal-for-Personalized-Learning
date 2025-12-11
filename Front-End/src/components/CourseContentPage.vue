<template>
  <NavBar @fetchData="fetchCourseContents" />
  <div class="course-page">
    <!-- Sidebar (20%) -->
    <div class="sidebar">
      <h2>Course Contents</h2>
      <button v-if="user.role == 'admin'" class="add-assignment-btn dlt" @click="deleteCourse">🗑 Delete This Course</button>
      <button v-if="user.role != 'student'" class="add-assignment-btn" @click="openAddAssignment(false)">➕ Add Assignment</button>
      <AddAssignments :isVisible="showAssignmentModal" :isUpdation="isUpdation" :assignmentData="this.assignmentData" @close="showAssignmentModal = false" @refresh="fetchCourseContents" />
      <button v-if="user.role != 'student'" class="add-assignment-btn" @click="openUpdateCourse(false)">⚙ Add New Content</button>
      <AddCourseContents :isVisible="showCourseContentModal" :isUpdation="isCourseUpdation" :contentData="this.contentData" @close="showCourseContentModal = false" @refresh="fetchCourseContents" />
      <AddQuestionForm :isVisible="showQuestionModal" :isUpdation="isQuestionUpdation" :assignmentId="this.assignmentId" :questionData="this.questionData" @close="showQuestionModal = false" @refresh="fetchAssignmentDetails(assignmentId)" />
      <div :style="{ height: user.role === 'student' ? '85vh' : '55vh', overflowY: 'auto' }">
      <ul>
        <li v-for="week in weeks" :key="week.week">
          <div class="week-header" @click="toggleWeek(week.week)">
            <span>Week {{ week.week }}</span>
            <span class="arrow" :class="{ rotated: activeWeek === week.week }">▼</span>
          </div>
          <ul v-show="activeWeek === week.week" class="content-list">
            <li v-for="content in week.contents" :key="content.id" class="content-item">
              <span @click="selectContent(content)" class="content-title">
                {{ content.title }}
              </span>
              <button v-if="user.role !== 'student' && !content.assignment_id" class="delete-btn" @click="deleteCourseContent(content.id, week.week, content.title)">🗑</button>
              <button v-if="user.role !== 'student' && content.assignment_id" class="delete-btn" @click="deleteAssignment(content.assignment_id, week.week, content.title)">🗑</button>
            </li>
          </ul>
        </li>
      </ul>
      </div>
    </div>

    <!-- Content Section (80%) -->
    <div class="content">
      <div class="header">
        <h2 v-if="selectedContent">{{ selectedContent.title }}</h2>
        <p v-else class="placeholder-text">Select a course content to start learning!</p>
        <p v-if="selectedContent && selectedContent.due_date" class="deadline">
          <strong>Deadline:</strong> {{ selectedContent.due_date }}
        </p>
        <button v-if="user.role !== 'student' && selectedContent && !selectedContent.assignment_id" class="update-course-btn" @click="openUpdateCourse(true)">⚙ Update Content</button>
        <button v-if="user.role !== 'student' && selectedContent?.assignment_id" class="update-course-btn" @click="openAddQuestion">➕ Add New Question</button>
        <button v-if="user.role !== 'student' && selectedContent?.assignment_id" class="update-course-btn" @click="openAddAssignment(true)">⚙ Update Assignment</button>       
      </div>
      
      <!-- Video Section -->
      <div class="video-container" v-if="selectedContent && selectedContent.video_link">
        <iframe :src="embedVideo(selectedContent.video_link)" frameborder="0" allowfullscreen></iframe>
      </div>
      <div class="scrollable">
      <!-- Assignments Section -->
      <div v-if="selectedContent && selectedContent.due_date">
        <div v-for="(question, index) in selectedAssignment.questions" :key="index" class="question-card">
          <p><strong>Q{{ index + 1 }}:</strong> {{ question.question_text }}</p>

          <!-- MCQ Type -->
          <div v-if="question.question_type === 'mcq'">
            <div v-for="(option, i) in question.choices" :key="i">
              <label>
                <input type="radio" :name="'question-' + index" :value="option" v-model="responses[index]" />
                {{ option }}
              </label>
            </div>
          </div>


          <!-- String Type -->
          <div v-if="question.question_type === 'string'">
            <label for="'question-' + index"></label>
            <input type="text" :id="'question-' + index" v-model="responses[index]" placeholder="Enter your answer here" class="text-input" />
          </div>

          <div v-if="user.role !== 'student'" class="question-actions">
            <button @click="updateQuestion(index)">✏ Update</button>
            <button @click="deleteQuestion(index)">🗑 Delete</button>
          </div>
        </div>

        <div class="submit-container">
          <button v-if="user.role === 'student'" class="submit-btn" @click="submitAssignment">📤 Submit Assignment</button>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/auth';
import NavBar from '@/components/icons/NavBar.vue'; 
import AddAssignments from '@/components/icons/AddAssignments.vue';
import AddCourseContents from '@/components/icons/AddCourseContents.vue';
import AddQuestionForm from '@/components/icons/AddQuestionForm.vue';


export default {
  name: "CourseContent",
  components: { NavBar, AddAssignments, AddCourseContents, AddQuestionForm },
  data() {
    return {
      user: JSON.parse(localStorage.getItem('user')) || "",
      weeks: [],
      activeWeek: null,
      selectedContent: null,
      selectedAssignment: { questions: [] },
      responses: [], // Store answers for each question
      showAssignmentModal: false,
      showCourseContentModal: false,
      showQuestionModal: false, 
      isUpdation: false,
      isCourseUpdation: false,
      isQuestionUpdation: false,
      assignmentData: null,
      contentData: null,
      questionData: null,
      assignmentId: null
    };
  },
  methods: {
    async fetchCourseContents() {
      const courseId = this.$route.query.id;
      if (!courseId) {
        console.error("Course ID is missing!");
        return;
      }
      
      try {
        const response = await api.get(`/course_contents/${courseId}`);
        const { course_contents, assignments } = response.data;
        // Grouping course contents and assignments together by week
        this.weeks = this.groupByWeek([...course_contents, ...assignments]);

        if (this.selectedContent && this.selectedContent.assignment_id) {
          // Determine if the current selected content has a due date
          const hasDueDate = !!this.selectedContent.due_date;

          // Find content based on whether it has a due date or not
          const updatedContent = this.weeks
            .flatMap(week => week.contents)
            .find(content =>
              hasDueDate
                ? content.due_date && content.assignment_id === this.selectedContent.assignment_id
                : !content.due_date && content.id === this.selectedContent.id
            );

          if (updatedContent) {
            this.selectedContent = updatedContent;
            // Find and assign the active week
            this.activeWeek = this.selectedContent.week || "";

            // Fetch assignment details if due date exists
            if (updatedContent.due_date) {
              this.fetchAssignmentDetails(updatedContent.assignment_id);
            }
          }
        } else if (this.selectedContent) {
          // Find content based on whether it has a due date or not
          const updatedContent = this.weeks
            .flatMap(week => week.contents)
            .find(content =>
              !content.due_date
                ? content.id === this.selectedContent.id
                : null
            );

          if (updatedContent) {
            this.selectedContent = updatedContent;
            // Find and assign the active week
            this.activeWeek = this.selectedContent.week || "";
          }
        }
      } catch (error) {
        console.error("Error fetching course contents and assignments:", error.response?.data?.message || error);
      }
    },

    groupByWeek(items) {
      const grouped = {};
      items.forEach(item => {
        const week = item.week || "Unspecified";
        if (!grouped[week]) grouped[week] = { contents: [] };
        
        grouped[week].contents.push(item);
      });

      // Sorting weeks in order
      return Object.keys(grouped)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(week => ({
          week,
          contents: grouped[week].contents
        }));
    },

    async fetchAssignmentDetails(assignmentId) {
      try {
        const response = await api.get(`/assignment/questions/${assignmentId}`);
        this.selectedAssignment = response.data;
        if (this.user.role === 'student') {
          // Extract submitted answers directly from the response
          this.responses = this.selectedAssignment.questions.map(q => q.submitted_answer);
        } else {
          this.responses = new Array(this.selectedAssignment.questions.length).fill(null);
        }
      } catch (error) {
        console.error("Error fetching assignment details:", error);
      }
    },


    selectContent(content) {
      this.selectedContent = content;
      if (content.assignment_id) {
        this.fetchAssignmentDetails(content.assignment_id);
      }
    },

    async deleteCourse() {
      if (!confirm(`Are you sure you want to delete the Entire Course?`)) {
        return;
      }
      try {
        await api.delete(`/delete_course/course/${this.$route.query.id}`);
        this.$router.push(`/admin/dashboard/${this.user.name}`);
      } catch (error) {
        console.error("Error deleting course:", error);
      }
    },

    async deleteCourseContent(contentId, week, title) {
      if (!confirm(`Are you sure you want to delete "${title}" from Week ${week}?`)) {
        return;
      }
      try {
        await api.delete(`/delete_course_content/${contentId}`);
        this.fetchCourseContents();
      } catch (error) {
        console.error("Error deleting content:", error);
      }
    },

    async deleteAssignment(assignmentId, week, title ) {
      if (!confirm(`Are you sure you want to delete assignment "${title}" from Week ${week}?`)) {
        return;
      }
      try {
        await api.delete(`/delete_assignment/${assignmentId}`);
        this.fetchCourseContents();
      } catch (error) {
        console.error("Error deleting content:", error);
      }
    },

    async submitAssignment() {
      if (!this.selectedContent.assignment_id) {
        alert("No assignment selected!");
        return;
      }
      try {
        const response = await api.post('/submit_or_update_answers', {
          
          assignment_id: this.selectedContent.assignment_id,
          answers: this.selectedAssignment.questions.map((q, index) => ({
            question_id: q.question_id,
            selected_answer: this.responses[index]
          }))
        });
        alert(response.data.message);
      } catch (error) {
        console.log("Submitting assignment with ID:", this.selectedContent.assignment_id);
        console.error("Error submitting assignment:", error);
        alert("Failed to submit assignment. Please try again.");
      }
    },

    updateQuestion(index) {
      this.questionData = this.selectedAssignment.questions[index]; // Pass the selected question data
      this.isQuestionUpdation = true;
      this.showQuestionModal = true; // Open the modal
    },

    openAddQuestion() {
      this.isQuestionUpdation = false;  
      this.questionData = null;    
      this.assignmentId = this.selectedContent.assignment_id     
      this.showQuestionModal = true;    
    },

    async deleteQuestion(index) {
      const question = this.selectedAssignment.questions[index];
      if (!confirm(`Are you sure you want to delete this question?\n\n"${question.question_text}"`)) return;

      try {
        await api.delete(`/delete_assignment_question/${question.question_id}`);
        alert("Question deleted successfully!");
        this.fetchAssignmentDetails(this.selectedContent.assignment_id);
      } catch (error) {
        console.error("Error deleting question:", error);
        alert("Failed to delete the question.");
      }
    },

    openAddAssignment(isUpdate) {
      this.isUpdation = isUpdate;
      this.showAssignmentModal = true;
      this.assignmentData = isUpdate ? this.selectedContent : null;
    },

    openUpdateCourse(isUpdate) {
      this.isCourseUpdation = true;
      this.showCourseContentModal = true;
      this.contentData = isUpdate ? this.selectedContent : null;
    },

    toggleWeek(weekNumber) {
      this.activeWeek = this.activeWeek === weekNumber ? null : weekNumber;
    },

    embedVideo(videoLink) {
      return videoLink.replace("watch?v=", "embed/");
    }
  },

  watch: {
    '$route': {
      handler() {
        this.fetchCourseContents();
      },
      immediate: true
    }
  },

};
</script>


<style scoped>
@import '@/assets/dashboardBody.css';
@import '@/assets/card.css';

.course-page {
  display: flex;
  height: 91vh;
  width: 100%;
  background: linear-gradient(120deg, #A9F1DF, #FFBBBB);
  color: #333;
  font-family: 'Arial', sans-serif;
}

.scrollable {
  overflow-y: auto;
  max-height: 75vh; /* Adjust height as needed to fit content */
}

.deadline {
  font-size: 16px;
  color: red;
  margin-bottom: 10px;
}

.question-card {
  position: relative;
  text-align: left;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  margin-bottom: 15px;
}

.question-actions {
  position: absolute;
  top: 25px;
  right: 25px;
}

.question-actions button {
  margin-left: 5px;
  background: #ff6666;
  color: white;
  border: none;
  padding: 5px 8px;
  border-radius: 5px;
  cursor: pointer;
}

.question-actions button:first-child {
  background: #4CAF50; /* Green for update */
}

.text-input {
  width: 100%;
  padding: 8px;
  margin-top: 5px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* Sidebar */
.sidebar {
  width: 20%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  color: white;
  padding: 20px;
  overflow-y: auto;
}

.sidebar h2 {
  margin-bottom: 15px;
  text-align: center;
  font-size: 20px;
}

.sidebar ul {
  list-style: none;
  padding: 0;
}

.sidebar li {
  margin-bottom: 5px;
}

.week-header {
  padding: 12px;
  background: #495057;
  cursor: pointer;
  border-radius: 5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.week-header:hover {
  background: #6c757d;
}

.arrow {
  transition: transform 0.3s ease;
}

.rotated {
  transform: rotate(180deg);
}

/* Dropdown animation */
.content-list {
  background: linear-gradient(90deg, #667eea, #764ba2);
  padding: 10px;
  border-radius: 5px;
  margin-top: 5px;
}

.content-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #868e96;
  border-radius: 5px;
  padding: 8px;
  margin-bottom: 5px;
}

.content-title {
  cursor: pointer;
  flex-grow: 1;
  transition: background 0.3s ease;
}

.content-title:hover {
  background: #adb5bd;
}

/* Delete button */
.delete-btn {
  background: red;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.delete-btn:hover {
  background: darkred;
}

.add-assignment-btn {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 16px;
  cursor: pointer;
}

.add-assignment-btn:hover {
  background: #218838;
}

.dlt {
  background: red; 
}

.dlt:hover {
  background: darkred;
}

/* Content Section */
.content {
  width: 80%;
  padding: 20px;
  text-align: center;
}

.content h2 {
  font-size: 24px;
  margin-bottom: 15px;
}

.video-container {
  margin-top: 20px;
}

.video-container iframe {
  width: 100%;
  height: 500px;
  border-radius: 10px;
}

.placeholder-text {
  font-size: 18px;
  color: #777;
  margin-top: 50px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.update-course-btn {
  background: #ff9800;
  color: white;
  padding: 8px 12px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.update-course-btn:hover {
  background: #e68900;
}

.submit-btn {
  background-color: #007bff; /* Bright blue */
  color: white;
  font-size: 18px;
  font-weight: bold;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.3s ease;
  box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2); /* Subtle shadow */
}

.submit-btn:hover {
  background-color: #0056b3; /* Darker blue on hover */
}

.submit-container {
  display: flex;
  justify-content: center; /* Centers horizontally */
  align-items: center; /* Centers vertically */
  margin-top: 20px;
}

</style>
