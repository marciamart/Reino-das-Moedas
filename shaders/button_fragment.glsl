#version 330 core
in vec3 ButtonColor;
out vec4 FragColor;
void main()
{
    FragColor = vec4(ButtonColor, 1.0);
}
